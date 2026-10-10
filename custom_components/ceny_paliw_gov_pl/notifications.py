"""Phone notifications for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from functools import partial
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from .api import FuelPriceData, PricePeriod
from .const import (
    CONF_NOTIFICATION_CUSTOM_MESSAGE,
    CONF_NOTIFICATION_CUSTOM_TITLE,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_FUELS,
    CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
    CONF_NOTIFICATION_ONLY_ON_CHANGE,
    DEFAULT_NOTIFICATION_CUSTOM_MESSAGE,
    DEFAULT_NOTIFICATION_CUSTOM_TITLE,
    DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
    DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
    DEVICE_ENABLED,
    DEVICE_FUELS,
    DEVICE_NAME,
    DEVICE_NOTIFICATION_MODE,
    DEVICE_NOTIFICATION_TIME,
    DEVICE_SERVICE,
    DOMAIN,
    FUEL_NAMES,
    FUELS,
    NOTIFICATION_DATA,
    NOTIFICATION_STORAGE_KEY_PREFIX,
    NOTIFICATION_STORAGE_VERSION,
    NOTIFICATION_TEST_TITLE,
    NOTIFICATION_TITLE,
    PHONE_STATUS_ERROR,
    PHONE_STATUS_FILTERED,
    PHONE_STATUS_NONE,
    PHONE_STATUS_SENT,
    PHONE_STATUS_WAITING,
    PHONE_NOTIFICATION_MODE_PUBLICATION,
    PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE,
    PHONE_NOTIFICATION_MODE_SCHEDULED,
    STATUS_NO_CHANGE,
    SIGNAL_NOTIFICATION_STATE_UPDATED,
    STATUS_NOT_PUBLISHED,
    UNIT_PRICE,
)
from .coordinator import FuelPriceCoordinator
from .phone_config import (
    configured_devices,
    default_device_name,
    normalize_fuels,
    normalize_notification_mode,
    time_from_string,
)

_LOGGER = logging.getLogger(__name__)


def mobile_app_notify_targets(hass: HomeAssistant) -> list[dict[str, str]]:
    """Return available mobile_app notify services as selector options."""
    notify_services = hass.services.async_services().get("notify", {})
    targets: list[dict[str, str]] = []
    for service_name in sorted(notify_services):
        if not service_name.startswith("mobile_app_"):
            continue
        target = f"notify.{service_name}"
        targets.append(
            {
                "value": target,
                "label": f"{default_device_name(target)} ({target})",
            }
        )
    return targets


def selected_fuels(
    options: Mapping[str, Any] | None,
    fuels_override: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """Return valid fuels selected for one notification."""
    if fuels_override is not None:
        return normalize_fuels(fuels_override)
    raw = (options or {}).get(CONF_NOTIFICATION_FUELS, list(FUELS))
    return normalize_fuels(raw)


def _format_price(value: Decimal | None) -> str:
    if value is None:
        return STATUS_NOT_PUBLISHED
    return f"{value:.2f}".replace(".", ",") + f" {UNIT_PRICE}"


def _price(period: PricePeriod | None, fuel: str) -> Decimal | None:
    if period is None:
        return None
    return period.prices.get(fuel)


def difference_grosz(
    today_period: PricePeriod | None,
    tomorrow_period: PricePeriod | None,
    fuel: str,
) -> int | None:
    """Return tomorrow minus today in grosz."""
    today = _price(today_period, fuel)
    tomorrow = _price(tomorrow_period, fuel)
    if today is None or tomorrow is None:
        return None
    difference = tomorrow - today
    return int(
        (difference * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def change_text(
    today_period: PricePeriod | None,
    tomorrow_period: PricePeriod | None,
    fuel: str,
) -> str:
    """Return the same human readable change text as the sensor."""
    grosz = difference_grosz(today_period, tomorrow_period, fuel)
    if grosz is None:
        return STATUS_NOT_PUBLISHED
    if grosz > 0:
        return f"drożej o {grosz}gr"
    if grosz < 0:
        return f"taniej o {abs(grosz)}gr"
    return STATUS_NO_CHANGE


def build_price_notification(
    data: FuelPriceData,
    fuels: list[str] | None = None,
) -> str:
    """Build the notification body with today, tomorrow and price changes."""
    date_text = data.tomorrow_date.strftime("%d.%m.%Y")
    lines = [f"Maksymalne ceny paliw na jutro, {date_text}"]

    for fuel in fuels or list(FUELS):
        today = _price(data.today, fuel)
        tomorrow = _price(data.tomorrow, fuel)
        lines.append(
            f"{FUEL_NAMES[fuel]}: dziś {_format_price(today)}, "
            f"jutro {_format_price(tomorrow)}, "
            f"{change_text(data.today, data.tomorrow, fuel)}"
        )

    return "\n".join(lines)


def build_not_published_notification(data: FuelPriceData) -> str:
    """Build a message for manual sending when tomorrow prices are missing."""
    date_text = data.tomorrow_date.strftime("%d.%m.%Y")
    return (
        f"Maksymalne ceny paliw na jutro, {date_text}\n"
        "Ministerstwo Energii nie opublikowało jeszcze cen na jutro."
    )


def _template_variables(data: FuelPriceData) -> dict[str, Any]:
    variables: dict[str, Any] = {
        "today_date": data.today_date.isoformat(),
        "tomorrow_date": data.tomorrow_date.isoformat(),
        "published": data.tomorrow is not None,
    }
    for fuel in FUELS:
        today = _price(data.today, fuel)
        tomorrow = _price(data.tomorrow, fuel)
        diff = difference_grosz(data.today, data.tomorrow, fuel)
        variables[fuel] = {
            "name": FUEL_NAMES[fuel],
            "today": float(today) if today is not None else None,
            "tomorrow": float(tomorrow) if tomorrow is not None else None,
            "today_text": _format_price(today),
            "tomorrow_text": _format_price(tomorrow),
            "change": change_text(data.today, data.tomorrow, fuel),
            "difference_grosz": diff,
        }
    return variables


def _render_custom_template(
    hass: HomeAssistant,
    raw_template: str,
    variables: dict[str, Any],
) -> str | None:
    """Render a Home Assistant template and fall back on error."""
    if not raw_template.strip():
        return None
    try:
        return str(
            Template(raw_template, hass).async_render(
                variables=variables,
                parse_result=False,
            )
        ).strip()
    except Exception as err:  # noqa: BLE001
        # Fail safely, including unexpected errors from custom templates.
        _LOGGER.error("Błąd szablonu powiadomienia: %s", err)
        return None


def build_notification_content(
    hass: HomeAssistant,
    data: FuelPriceData,
    options: Mapping[str, Any] | None = None,
    *,
    fuels_override: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, str]:
    """Build title and body, including optional Home Assistant templates."""
    options = options or {}
    fuels = selected_fuels(options, fuels_override)
    default_message = (
        build_price_notification(data, fuels)
        if data.tomorrow is not None
        else build_not_published_notification(data)
    )
    variables = _template_variables(data)

    custom_title = str(
        options.get(CONF_NOTIFICATION_CUSTOM_TITLE, DEFAULT_NOTIFICATION_CUSTOM_TITLE)
        or ""
    )
    custom_message = str(
        options.get(
            CONF_NOTIFICATION_CUSTOM_MESSAGE,
            DEFAULT_NOTIFICATION_CUSTOM_MESSAGE,
        )
        or ""
    )

    title = _render_custom_template(hass, custom_title, variables) or NOTIFICATION_TITLE
    message = _render_custom_template(hass, custom_message, variables) or default_message
    return title, message


def has_relevant_change(
    data: FuelPriceData,
    options: Mapping[str, Any] | None,
    *,
    fuels_override: list[str] | tuple[str, ...] | None = None,
    force: bool = False,
) -> bool:
    """Return whether an automatic notification passes change filters."""
    options = options or {}
    if not force and not bool(
        options.get(
            CONF_NOTIFICATION_ONLY_ON_CHANGE,
            DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
        )
    ):
        return True
    if data.today is None or data.tomorrow is None:
        return False

    try:
        threshold = max(
            0,
            int(
                options.get(
                    CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
                    DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
                )
            ),
        )
    except (TypeError, ValueError):
        threshold = DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ

    required = max(1, threshold)
    for fuel in selected_fuels(options, fuels_override):
        difference = difference_grosz(data.today, data.tomorrow, fuel)
        if difference is not None and abs(difference) >= required:
            return True
    return False


async def async_send_mobile_notification(
    hass: HomeAssistant,
    target: str,
    title: str,
    message: str,
) -> None:
    """Send a mobile_app notification."""
    if not target.startswith("notify.mobile_app_"):
        raise ValueError(f"Nieobsługiwany cel powiadomień: {target}")

    service = target.split(".", 1)[1]
    if not hass.services.has_service("notify", service):
        raise ValueError(f"Usługa {target} nie jest dostępna")

    await hass.services.async_call(
        "notify",
        service,
        {
            "title": title,
            "message": message,
            "data": dict(NOTIFICATION_DATA),
        },
        blocking=True,
    )


async def async_send_test_notification(
    hass: HomeAssistant,
    target: str,
    display_name: str,
) -> None:
    """Send a test notification to one configured phone."""
    message = (
        "Test powiadomienia z integracji Maksymalne Ceny Paliw GOV.PL.\n\n"
        f"Urządzenie: {display_name}"
    )
    await async_send_mobile_notification(
        hass,
        target,
        NOTIFICATION_TEST_TITLE,
        message,
    )


async def async_send_current_notification(
    hass: HomeAssistant,
    target: str,
    data: FuelPriceData,
    options: Mapping[str, Any] | None = None,
    *,
    fuels_override: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Send the same content used by the normal daily notification."""
    title, message = build_notification_content(
        hass,
        data,
        options,
        fuels_override=fuels_override,
    )
    await async_send_mobile_notification(hass, target, title, message)


class FuelPriceNotificationManager:
    """Schedule and send per-phone fuel price notifications."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: FuelPriceCoordinator,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(
            hass,
            NOTIFICATION_STORAGE_VERSION,
            f"{NOTIFICATION_STORAGE_KEY_PREFIX}.{entry.entry_id}",
        )
        self._state: dict[str, Any] = {}
        self._unsub_times: dict[str, CALLBACK_TYPE] = {}
        self._unsub_coordinator: CALLBACK_TYPE | None = None
        self._send_lock = asyncio.Lock()
        self.last_send_status = "Brak wysyłki"
        self.last_send_at: datetime | None = None

    @property
    def devices(self) -> list[dict[str, Any]]:
        """Return normalized phone configuration."""
        return configured_devices(self.entry.options)

    @property
    def enabled_devices(self) -> list[dict[str, Any]]:
        """Return phones enabled for automatic notifications."""
        return [
            device
            for device in self.devices
            if device.get(DEVICE_ENABLED, True) and device.get(DEVICE_SERVICE)
        ]

    @property
    def missing_enabled_targets(self) -> list[str]:
        """Return configured enabled targets that no longer exist."""
        missing: list[str] = []
        for device in self.enabled_devices:
            target = str(device.get(DEVICE_SERVICE, ""))
            if not target.startswith("notify."):
                missing.append(target)
                continue
            service = target.split(".", 1)[1]
            if not self.hass.services.has_service("notify", service):
                missing.append(target)
        return missing

    def phone_status(self, target: str) -> str:
        """Return the persisted last automatic or manual notification status."""
        raw = self._state.get("phone_status", {})
        if not isinstance(raw, Mapping):
            return PHONE_STATUS_NONE
        value = raw.get(target)
        return str(value) if value else PHONE_STATUS_NONE

    def phone_last_sent_at(self, target: str) -> datetime | None:
        """Return the persisted time of the last successfully sent notification."""
        raw = self._state.get("phone_last_sent_at", {})
        if not isinstance(raw, Mapping):
            return None
        value = raw.get(target)
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    def phone_waiting(self, target: str) -> bool:
        """Return whether a phone is waiting for a publication or scheduled delivery."""
        if target in self._waiting_services():
            return True
        device = self._device_map().get(target)
        if device is None:
            return False
        mode = normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))
        return (
            mode in {
                PHONE_NOTIFICATION_MODE_PUBLICATION,
                PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE,
            }
            and self.phone_status(target) == PHONE_STATUS_WAITING
        )

    def _daily_publication_key(self) -> str | None:
        """Build an identifier for today's resolved tomorrow-price delivery."""
        period = self.coordinator.data.tomorrow
        if period is None:
            return None
        return "|".join((self.coordinator.data.tomorrow_date.isoformat(), self._source_publication_key() or ""))

    def _source_publication_key(self) -> str | None:
        """Build an identifier that stays stable across a multi-day publication."""
        period = self.coordinator.data.tomorrow
        if period is None:
            return None
        prices = "|".join(f"{fuel}:{period.prices.get(fuel)}" for fuel in FUELS)
        published = period.published_on.isoformat() if period.published_on else ""
        return "|".join(
            (
                period.valid_from.isoformat(),
                period.valid_to.isoformat(),
                published,
                prices,
                period.source_url,
            )
        )

    def _delivered_publications(self) -> dict[str, str]:
        """Return persisted daily publication identifiers delivered to phones."""
        raw = self._state.get("delivered_publications", {})
        if not isinstance(raw, Mapping):
            return {}
        return {str(target): str(value) for target, value in raw.items() if value}

    def _delivered_source_publications(self) -> dict[str, str]:
        """Return persisted source-publication identifiers delivered to phones."""
        raw = self._state.get("delivered_source_publications", {})
        if not isinstance(raw, Mapping):
            return {}
        return {str(target): str(value) for target, value in raw.items() if value}

    async def _async_record_phone_status(
        self,
        target: str,
        status: str,
        *,
        sent_at: datetime | None = None,
    ) -> None:
        """Persist one phone status and notify entities listening for state changes."""
        statuses = dict(self._state.get("phone_status", {}))
        statuses[target] = status
        self._state["phone_status"] = statuses
        if sent_at is not None:
            sent_times = dict(self._state.get("phone_last_sent_at", {}))
            sent_times[target] = sent_at.isoformat()
            self._state["phone_last_sent_at"] = sent_times
        await self._async_save_state()
        async_dispatcher_send(self.hass, SIGNAL_NOTIFICATION_STATE_UPDATED, target)

    async def async_start(self) -> None:
        """Start notification listeners."""
        self._state = await self._store.async_load() or {}
        self._prune_removed_targets_from_state()
        self._sync_target_repairs()
        await self._async_save_state()
        self._unsub_coordinator = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        await self.async_reschedule()
        await self._async_evaluate_current_day()
        for device in self.devices:
            target = str(device.get(DEVICE_SERVICE, ""))
            if target:
                async_dispatcher_send(self.hass, SIGNAL_NOTIFICATION_STATE_UPDATED, target)

    async def async_stop(self) -> None:
        """Stop notification listeners."""
        self._cancel_time_listeners()
        if self._unsub_coordinator is not None:
            self._unsub_coordinator()
            self._unsub_coordinator = None
        issue_ids = self._stored_target_issue_ids()
        for device in self.devices:
            target = str(device.get(DEVICE_SERVICE, ""))
            if target:
                issue_ids.add(self._target_issue_id(target))
        for issue_id in issue_ids:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    async def async_options_changed(self) -> None:
        """Apply dashboard changes to per-phone scheduling immediately."""
        self._prune_removed_targets_from_state()
        self._sync_target_repairs()
        self._normalize_waiting_targets()
        await self._async_save_state()
        await self.async_reschedule()
        await self._async_evaluate_current_day()

    async def async_reschedule(self) -> None:
        """Create daily time listeners only for phones using scheduled mode."""
        self._cancel_time_listeners()
        for device in self.enabled_devices:
            mode = normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))
            if mode != PHONE_NOTIFICATION_MODE_SCHEDULED:
                continue
            target = str(device[DEVICE_SERVICE])
            notification_time = time_from_string(device.get(DEVICE_NOTIFICATION_TIME))
            self._unsub_times[target] = async_track_time_change(
                self.hass,
                partial(self._async_scheduled_target, target),
                hour=notification_time.hour,
                minute=notification_time.minute,
                second=notification_time.second,
            )

    def _cancel_time_listeners(self) -> None:
        for unsubscribe in self._unsub_times.values():
            unsubscribe()
        self._unsub_times.clear()

    @staticmethod
    def _target_issue_id(target: str) -> str:
        return "missing_notify_target_" + "".join(
            char if char.isalnum() else "_" for char in target.lower()
        )

    def _stored_target_issue_ids(self) -> set[str]:
        """Return repair issue IDs created for notification targets."""
        raw = self._state.get("target_issue_ids", [])
        if not isinstance(raw, list):
            return set()
        return {str(issue_id) for issue_id in raw if str(issue_id)}

    def _prune_removed_targets_from_state(self) -> None:
        """Remove persisted notification state for phones no longer configured."""
        current_targets = {
            str(device.get(DEVICE_SERVICE, ""))
            for device in self.devices
            if device.get(DEVICE_SERVICE)
        }
        for key in (
            "phone_status",
            "phone_last_sent_at",
            "delivered_publications",
            "delivered_source_publications",
        ):
            raw = self._state.get(key)
            if not isinstance(raw, Mapping):
                continue
            cleaned = {
                str(target): value
                for target, value in raw.items()
                if str(target) in current_targets
            }
            if cleaned:
                self._state[key] = cleaned
            else:
                self._state.pop(key, None)

        for key in ("notified_services", "waiting_services"):
            raw = self._state.get(key)
            if not isinstance(raw, list):
                continue
            cleaned = [
                str(target) for target in raw if str(target) in current_targets
            ]
            if cleaned:
                self._state[key] = sorted(set(cleaned))
            else:
                self._state.pop(key, None)

        if "notified_services" not in self._state:
            self._state.pop("notified_for", None)
        if "waiting_services" not in self._state:
            self._state.pop("waiting_for_date", None)

    def _sync_target_repairs(self) -> None:
        """Create or clear repair warnings for renamed or missing phones."""
        current_issue_ids: set[str] = set()
        for device in self.devices:
            target = str(device.get(DEVICE_SERVICE, ""))
            if not target:
                continue
            issue_id = self._target_issue_id(target)
            current_issue_ids.add(issue_id)
            service = target.split(".", 1)[1] if target.startswith("notify.") else ""
            available = bool(service and self.hass.services.has_service("notify", service))
            enabled = bool(device.get(DEVICE_ENABLED, True))
            if available or not enabled:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
                continue
            display_name = str(device.get(DEVICE_NAME) or default_device_name(target))
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="notification_target_missing",
                translation_placeholders={
                    "name": display_name,
                    "target": target,
                },
            )

        for issue_id in self._stored_target_issue_ids() - current_issue_ids:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        self._state["target_issue_ids"] = sorted(current_issue_ids)

    def _target_date(self) -> str:
        return self.coordinator.data.tomorrow_date.isoformat()

    def _notified_services(self) -> set[str]:
        if self._state.get("notified_for") != self._target_date():
            return set()
        services = self._state.get("notified_services", [])
        if not isinstance(services, list):
            return set()
        return {str(service) for service in services}

    def _waiting_services(self) -> set[str]:
        if self._state.get("waiting_for_date") != self._target_date():
            return set()
        services = self._state.get("waiting_services", [])
        if not isinstance(services, list):
            return set()
        return {str(service) for service in services}

    def _device_map(self) -> dict[str, dict[str, Any]]:
        return {
            str(device[DEVICE_SERVICE]): device
            for device in self.devices
            if device.get(DEVICE_SERVICE)
        }

    def _enabled_device_map(self) -> dict[str, dict[str, Any]]:
        return {
            str(device[DEVICE_SERVICE]): device
            for device in self.enabled_devices
            if device.get(DEVICE_SERVICE)
        }

    def _is_delivered(self, target: str, device: Mapping[str, Any]) -> bool:
        """Return whether the current automatic delivery is already handled."""
        mode = normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))
        daily_key = self._daily_publication_key()
        source_key = self._source_publication_key()
        delivered_daily = self._delivered_publications()

        if mode == PHONE_NOTIFICATION_MODE_SCHEDULED:
            if daily_key is not None and target in delivered_daily:
                return delivered_daily[target] == daily_key
            return target in self._notified_services()

        if source_key is None:
            return False
        delivered_source = self._delivered_source_publications()
        if target in delivered_source:
            return delivered_source[target] == source_key

        legacy_daily = delivered_daily.get(target)
        if legacy_daily:
            _prefix, separator, legacy_source = legacy_daily.partition("|")
            return bool(separator and legacy_source == source_key)
        return target in self._notified_services()

    def _normalize_waiting_targets(self) -> None:
        """Drop scheduled waits for disabled phones, other modes or old dates."""
        if self._state.get("waiting_for_date") != self._target_date():
            self._state.pop("waiting_for_date", None)
            self._state.pop("waiting_services", None)
            return

        now = dt_util.now()
        now_seconds = now.hour * 3600 + now.minute * 60 + now.second
        enabled = self._enabled_device_map()
        waiting: set[str] = set()
        for target in self._waiting_services():
            device = enabled.get(target)
            if device is None:
                continue
            if normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE)) != PHONE_NOTIFICATION_MODE_SCHEDULED:
                continue
            scheduled = time_from_string(device.get(DEVICE_NOTIFICATION_TIME))
            scheduled_seconds = scheduled.hour * 3600 + scheduled.minute * 60 + scheduled.second
            if now_seconds >= scheduled_seconds and not self._is_delivered(target, device):
                waiting.add(target)

        if waiting:
            self._state["waiting_for_date"] = self._target_date()
            self._state["waiting_services"] = sorted(waiting)
        else:
            self._state.pop("waiting_for_date", None)
            self._state.pop("waiting_services", None)

    async def _async_save_state(self) -> None:
        await self._store.async_save(self._state)

    async def _async_add_waiting(
        self,
        target: str,
        status: str = PHONE_STATUS_WAITING,
    ) -> None:
        waiting = self._waiting_services()
        waiting.add(target)
        self._state["waiting_for_date"] = self._target_date()
        self._state["waiting_services"] = sorted(waiting)
        await self._async_save_state()
        await self._async_record_phone_status(target, status)

    async def _async_remove_waiting(self, targets: set[str]) -> None:
        waiting = self._waiting_services()
        waiting.difference_update(targets)
        if waiting:
            self._state["waiting_for_date"] = self._target_date()
            self._state["waiting_services"] = sorted(waiting)
        else:
            self._state.pop("waiting_for_date", None)
            self._state.pop("waiting_services", None)
        await self._async_save_state()

    async def _async_mark_delivered(self, targets: set[str]) -> None:
        """Persist daily and source-publication delivery keys for targets."""
        if not targets:
            return

        daily_key = self._daily_publication_key()
        if daily_key is not None:
            delivered_daily = self._delivered_publications()
            for target in targets:
                delivered_daily[target] = daily_key
            self._state["delivered_publications"] = delivered_daily

        source_key = self._source_publication_key()
        if source_key is not None:
            delivered_source = self._delivered_source_publications()
            for target in targets:
                delivered_source[target] = source_key
            self._state["delivered_source_publications"] = delivered_source

        notified = self._notified_services()
        notified.update(targets)
        self._state["notified_for"] = self._target_date()
        self._state["notified_services"] = sorted(notified)

        waiting = self._waiting_services()
        waiting.difference_update(targets)
        if waiting:
            self._state["waiting_for_date"] = self._target_date()
            self._state["waiting_services"] = sorted(waiting)
        else:
            self._state.pop("waiting_for_date", None)
            self._state.pop("waiting_services", None)
        await self._async_save_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync_target_repairs()
        self.hass.async_create_task(
            self._async_handle_coordinator_update(),
            "Maksymalne Ceny Paliw GOV.PL powiadomienia po aktualizacji danych",
        )

    async def _async_handle_coordinator_update(self) -> None:
        await self._async_evaluate_current_day()

    async def _async_scheduled_target(self, target: str, _now: datetime) -> None:
        """Handle the configured daily time for one phone."""
        device = self._enabled_device_map().get(target)
        if device is None:
            return
        if normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE)) != PHONE_NOTIFICATION_MODE_SCHEDULED:
            return
        if self._is_delivered(target, device):
            return

        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success:
            return
        device = self._enabled_device_map().get(target)
        if device is None or self._is_delivered(target, device):
            return

        if self.coordinator.data.tomorrow is not None:
            await self._async_send_devices(
                [device],
                mark_delivered=True,
                automatic=True,
            )
            return
        await self._async_add_waiting(target)

    async def _async_evaluate_current_day(self) -> None:
        """Evaluate publication modes and catch up scheduled phones."""
        publication_devices: list[dict[str, Any]] = []
        scheduled_due: list[dict[str, Any]] = []
        now = dt_util.now()
        now_seconds = now.hour * 3600 + now.minute * 60 + now.second

        for device in self.enabled_devices:
            target = str(device[DEVICE_SERVICE])
            mode = normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))

            if mode in {
                PHONE_NOTIFICATION_MODE_PUBLICATION,
                PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE,
            }:
                if self.coordinator.data.tomorrow is None:
                    if self.phone_status(target) != PHONE_STATUS_WAITING:
                        await self._async_record_phone_status(target, PHONE_STATUS_WAITING)
                    continue
                if not self._is_delivered(target, device):
                    publication_devices.append(device)
                continue

            if mode != PHONE_NOTIFICATION_MODE_SCHEDULED:
                continue
            if self._is_delivered(target, device):
                continue
            scheduled = time_from_string(device.get(DEVICE_NOTIFICATION_TIME))
            scheduled_seconds = scheduled.hour * 3600 + scheduled.minute * 60 + scheduled.second
            if now_seconds >= scheduled_seconds:
                scheduled_due.append(device)

        if publication_devices and self.coordinator.data.tomorrow is not None:
            await self._async_send_devices(
                publication_devices,
                mark_delivered=True,
                automatic=True,
            )

        if not scheduled_due:
            return
        if self.coordinator.data.tomorrow is not None:
            await self._async_send_devices(
                scheduled_due,
                mark_delivered=True,
                automatic=True,
            )
            return
        for device in scheduled_due:
            await self._async_add_waiting(str(device[DEVICE_SERVICE]))

    async def async_send_now_to_all(
        self,
        *,
        devices_override: list[dict[str, Any]] | None = None,
        options_override: Mapping[str, Any] | None = None,
    ) -> int:
        """Send the current daily-format notification to all enabled phones."""
        self._sync_target_repairs()
        source_devices = (
            devices_override if devices_override is not None else self.enabled_devices
        )
        devices = [
            dict(device)
            for device in source_devices
            if device.get(DEVICE_ENABLED, True) and device.get(DEVICE_SERVICE)
        ]
        return await self._async_send_devices(
            devices,
            mark_delivered=self.coordinator.data.tomorrow is not None,
            automatic=False,
            options_override=options_override,
        )

    async def async_send_now_to_target(
        self,
        target: str,
        *,
        options_override: Mapping[str, Any] | None = None,
        fuels_override: list[str] | tuple[str, ...] | None = None,
        mode_override: str | None = None,
        device_override: Mapping[str, Any] | None = None,
    ) -> bool:
        """Send the current daily-format notification to one configured phone."""
        device: Mapping[str, Any] | None = self._device_map().get(target)
        if (
            device_override is not None
            and str(device_override.get(DEVICE_SERVICE, "")) == target
        ):
            device = device_override
        if device is None:
            return False
        selected_device = dict(device)
        if fuels_override is not None:
            selected_device[DEVICE_FUELS] = normalize_fuels(fuels_override)
        if mode_override is not None:
            selected_device[DEVICE_NOTIFICATION_MODE] = normalize_notification_mode(
                mode_override
            )
        count = await self._async_send_devices(
            [selected_device],
            mark_delivered=self.coordinator.data.tomorrow is not None,
            automatic=False,
            options_override=options_override,
        )
        return bool(count)

    async def _async_send_devices(
        self,
        devices: list[dict[str, Any]],
        *,
        mark_delivered: bool,
        automatic: bool,
        options_override: Mapping[str, Any] | None = None,
    ) -> int:
        """Send individualized notification content to a list of phones."""
        if not devices:
            self.last_send_status = "Brak włączonych telefonów do wysyłki"
            return 0

        async with self._send_lock:
            successful: set[str] = set()
            filtered: set[str] = set()
            attempted_targets: set[str] = set()

            for device in devices:
                target = str(device.get(DEVICE_SERVICE, ""))
                if not target:
                    continue
                if automatic and self._is_delivered(target, device):
                    continue
                fuels = normalize_fuels(device.get(DEVICE_FUELS))
                notification_options = (
                    options_override
                    if options_override is not None
                    else self.entry.options
                )
                mode = normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))
                force_change = (
                    automatic
                    and mode == PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE
                )
                if automatic and not has_relevant_change(
                    self.coordinator.data,
                    notification_options,
                    fuels_override=fuels,
                    force=force_change,
                ):
                    filtered.add(target)
                    continue

                title, message = build_notification_content(
                    self.hass,
                    self.coordinator.data,
                    notification_options,
                    fuels_override=fuels,
                )
                display_name = str(device.get(DEVICE_NAME) or default_device_name(target))
                attempted_targets.add(target)
                try:
                    await async_send_mobile_notification(
                        self.hass,
                        target,
                        title,
                        message,
                    )
                except Exception:  # noqa: BLE001
                    _LOGGER.exception(
                        "Nie udało się wysłać powiadomienia na %s (%s)",
                        display_name,
                        target,
                    )
                else:
                    successful.add(target)

            if automatic and not attempted_targets and not filtered:
                # Another concurrent automatic task may have delivered every
                # target while this task was waiting for the send lock. In that
                # case there is nothing to report and the previous send status
                # must stay untouched.
                return 0

            handled = successful | filtered
            failed = attempted_targets - successful
            if mark_delivered and handled:
                await self._async_mark_delivered(handled)

            sent_at = dt_util.now()
            for target in sorted(successful):
                await self._async_record_phone_status(
                    target, PHONE_STATUS_SENT, sent_at=sent_at
                )
            for target in sorted(filtered):
                await self._async_record_phone_status(target, PHONE_STATUS_FILTERED)
            for target in sorted(failed):
                await self._async_record_phone_status(target, PHONE_STATUS_ERROR)

            self.last_send_at = sent_at
            if filtered and not attempted_targets:
                self.last_send_status = f"Pominięto filtrem: {len(filtered)}"
            else:
                self.last_send_status = (
                    f"Wysłano: {len(successful)}/{len(attempted_targets)}; "
                    f"pominięto filtrem: {len(filtered)}"
                )
            return len(successful)
