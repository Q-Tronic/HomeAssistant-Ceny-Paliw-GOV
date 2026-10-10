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
from homeassistant.exceptions import TemplateError
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
    except TemplateError as err:
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
) -> bool:
    """Return whether an automatic notification passes change filters."""
    options = options or {}
    if not bool(
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
        """Return whether a phone is waiting for tomorrow prices to be published."""
        return target in self._waiting_services()

    def _publication_key(self) -> str | None:
        """Build a stable identifier for the currently resolved tomorrow publication."""
        period = self.coordinator.data.tomorrow
        if period is None:
            return None
        prices = "|".join(
            f"{fuel}:{period.prices.get(fuel)}"
            for fuel in FUELS
        )
        published = period.published_on.isoformat() if period.published_on else ""
        return "|".join(
            (
                self.coordinator.data.tomorrow_date.isoformat(),
                period.valid_from.isoformat(),
                period.valid_to.isoformat(),
                published,
                prices,
                period.source_url,
            )
        )

    def _delivered_publications(self) -> dict[str, str]:
        """Return persisted publication identifiers delivered to each phone."""
        raw = self._state.get("delivered_publications", {})
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
        self._sync_target_repairs()
        self._unsub_coordinator = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        await self.async_reschedule()
        await self._async_evaluate_current_day()
        for device in self.devices:
            target = str(device.get(DEVICE_SERVICE, ""))
            if target:
                async_dispatcher_send(
                    self.hass, SIGNAL_NOTIFICATION_STATE_UPDATED, target
                )

    async def async_stop(self) -> None:
        """Stop notification listeners."""
        self._cancel_time_listeners()
        if self._unsub_coordinator is not None:
            self._unsub_coordinator()
            self._unsub_coordinator = None
        for device in self.devices:
            target = str(device.get(DEVICE_SERVICE, ""))
            if target:
                ir.async_delete_issue(
                    self.hass,
                    DOMAIN,
                    self._target_issue_id(target),
                )

    async def async_options_changed(self) -> None:
        """Apply dashboard changes to per-phone scheduling immediately."""
        self._sync_target_repairs()
        self._normalize_waiting_targets()
        await self._async_save_state()
        await self.async_reschedule()
        await self._async_evaluate_current_day()

    async def async_reschedule(self) -> None:
        """Create one daily time listener for each enabled phone."""
        self._cancel_time_listeners()
        for device in self.enabled_devices:
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

    def _sync_target_repairs(self) -> None:
        """Create or clear repair warnings for renamed or missing phones."""
        for device in self.devices:
            target = str(device.get(DEVICE_SERVICE, ""))
            if not target:
                continue
            issue_id = self._target_issue_id(target)
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

    def _is_notified(self, target: str) -> bool:
        publication_key = self._publication_key()
        if publication_key is not None:
            delivered = self._delivered_publications()
            if target in delivered:
                return delivered[target] == publication_key
        return target in self._notified_services()

    def _normalize_waiting_targets(self) -> None:
        """Drop waits for disabled phones, future times or old target dates."""
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
            scheduled = time_from_string(device.get(DEVICE_NOTIFICATION_TIME))
            scheduled_seconds = scheduled.hour * 3600 + scheduled.minute * 60 + scheduled.second
            if now_seconds >= scheduled_seconds and not self._is_notified(target):
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

    async def _async_mark_notified(self, targets: set[str]) -> None:
        if not targets:
            return
        notified = self._notified_services()
        notified.update(targets)
        self._state["notified_for"] = self._target_date()
        self._state["notified_services"] = sorted(notified)

        publication_key = self._publication_key()
        if publication_key is not None:
            delivered = self._delivered_publications()
            for target in targets:
                delivered[target] = publication_key
            self._state["delivered_publications"] = delivered

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
        if self.coordinator.data.tomorrow is None:
            return
        await self._async_evaluate_current_day()

    async def _async_scheduled_target(self, target: str, _now: datetime) -> None:
        """Handle the configured daily time for one phone."""
        device = self._enabled_device_map().get(target)
        if device is None or self._is_notified(target):
            return

        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success:
            return
        if self._is_notified(target):
            return

        if self.coordinator.data.tomorrow is not None:
            await self._async_send_devices([device], mark_notified=True, apply_filters=True)
            return
        await self._async_add_waiting(target)

    async def _async_evaluate_current_day(self) -> None:
        """Catch up phones whose configured time has already passed."""
        now = dt_util.now()
        now_seconds = now.hour * 3600 + now.minute * 60 + now.second
        due: list[dict[str, Any]] = []
        for device in self.enabled_devices:
            target = str(device[DEVICE_SERVICE])
            if self._is_notified(target):
                continue
            scheduled = time_from_string(device.get(DEVICE_NOTIFICATION_TIME))
            scheduled_seconds = scheduled.hour * 3600 + scheduled.minute * 60 + scheduled.second
            if now_seconds >= scheduled_seconds:
                due.append(device)

        if not due:
            return
        if self.coordinator.data.tomorrow is not None:
            await self._async_send_devices(due, mark_notified=True, apply_filters=True)
            return
        for device in due:
            await self._async_add_waiting(str(device[DEVICE_SERVICE]))

    async def async_send_now_to_all(self) -> int:
        """Send the current daily-format notification to all enabled phones."""
        self._sync_target_repairs()
        return await self._async_send_devices(
            self.enabled_devices,
            mark_notified=self.coordinator.data.tomorrow is not None,
            apply_filters=False,
        )

    async def async_send_now_to_target(
        self,
        target: str,
        *,
        options_override: Mapping[str, Any] | None = None,
        fuels_override: list[str] | tuple[str, ...] | None = None,
    ) -> bool:
        """Send the current daily-format notification to one configured phone."""
        device = self._device_map().get(target)
        if device is None:
            return False
        selected_device = dict(device)
        if fuels_override is not None:
            selected_device[DEVICE_FUELS] = normalize_fuels(fuels_override)
        count = await self._async_send_devices(
            [selected_device],
            mark_notified=self.coordinator.data.tomorrow is not None,
            apply_filters=False,
            options_override=options_override,
        )
        return bool(count)

    async def _async_send_devices(
        self,
        devices: list[dict[str, Any]],
        *,
        mark_notified: bool,
        apply_filters: bool,
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
                fuels = normalize_fuels(device.get(DEVICE_FUELS))
                notification_options = (
                    options_override
                    if options_override is not None
                    else self.entry.options
                )
                if apply_filters and not has_relevant_change(
                    self.coordinator.data,
                    notification_options,
                    fuels_override=fuels,
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

            handled = successful | filtered
            failed = attempted_targets - successful
            if mark_notified:
                if handled:
                    await self._async_mark_notified(handled)
                for target in sorted(failed):
                    await self._async_add_waiting(target, PHONE_STATUS_ERROR)

            sent_at = dt_util.now()
            for target in sorted(successful):
                await self._async_record_phone_status(
                    target, PHONE_STATUS_SENT, sent_at=sent_at
                )
            for target in sorted(filtered):
                await self._async_record_phone_status(target, PHONE_STATUS_FILTERED)
            if not mark_notified:
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
