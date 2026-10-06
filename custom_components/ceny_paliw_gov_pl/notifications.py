"""Phone notifications for Ceny paliw GOV.PL."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import issue_registry as ir
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
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_ONLY_ON_CHANGE,
    CONF_NOTIFICATION_TIME,
    CONF_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFICATION_CUSTOM_MESSAGE,
    DEFAULT_NOTIFICATION_CUSTOM_TITLE,
    DEFAULT_NOTIFICATION_FUELS,
    DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
    DEFAULT_NOTIFICATION_MODE,
    DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEVICE_ENABLED,
    DEVICE_NAME,
    DEVICE_SERVICE,
    DOMAIN,
    FUEL_NAMES,
    FUELS,
    NOTIFICATION_DATA,
    NOTIFICATION_MODE_ON_PUBLICATION,
    NOTIFICATION_MODE_SCHEDULED,
    NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION,
    NOTIFICATION_STORAGE_KEY_PREFIX,
    NOTIFICATION_STORAGE_VERSION,
    NOTIFICATION_TEST_TITLE,
    NOTIFICATION_TITLE,
    STATUS_NO_CHANGE,
    STATUS_NOT_PUBLISHED,
    UNIT_PRICE,
)
from .coordinator import FuelPriceCoordinator

_LOGGER = logging.getLogger(__name__)


def default_device_name(target: str) -> str:
    """Build a readable default name from a mobile_app notify target."""
    service = target.removeprefix("notify.")
    service = service.removeprefix("mobile_app_")
    if not service:
        return target
    return service.replace("_", " ").strip().title()


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


def selected_fuels(options: Mapping[str, Any] | None) -> list[str]:
    """Return valid fuels selected for notifications."""
    raw = (options or {}).get(CONF_NOTIFICATION_FUELS, DEFAULT_NOTIFICATION_FUELS)
    if not isinstance(raw, list):
        return list(FUELS)
    fuels = [str(fuel) for fuel in raw if str(fuel) in FUELS]
    return fuels or list(FUELS)


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
    lines = [f"Ceny paliw na jutro, {date_text}", ""]

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
    """Build a message for scheduled mode when tomorrow prices are missing."""
    date_text = data.tomorrow_date.strftime("%d.%m.%Y")
    return (
        f"Ceny paliw na jutro, {date_text}\n\n"
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
) -> tuple[str, str]:
    """Build title and body, including optional Home Assistant templates."""
    options = options or {}
    fuels = selected_fuels(options)
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
    for fuel in selected_fuels(options):
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
        "Test powiadomienia z integracji Ceny paliw GOV.PL.\n\n"
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
) -> None:
    """Send the same content used by the normal daily notification."""
    title, message = build_notification_content(hass, data, options)
    await async_send_mobile_notification(hass, target, title, message)


class FuelPriceNotificationManager:
    """Schedule and send fuel price notifications."""

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
        self._unsub_time: CALLBACK_TYPE | None = None
        self._unsub_coordinator: CALLBACK_TYPE | None = None
        self._send_lock = asyncio.Lock()
        self.last_send_status = "Brak wysyłki"
        self.last_send_at: datetime | None = None

    @property
    def enabled(self) -> bool:
        return bool(
            self.entry.options.get(
                CONF_NOTIFICATIONS_ENABLED,
                DEFAULT_NOTIFICATIONS_ENABLED,
            )
        )

    @property
    def mode(self) -> str:
        return str(
            self.entry.options.get(
                CONF_NOTIFICATION_MODE,
                DEFAULT_NOTIFICATION_MODE,
            )
        )

    @property
    def notification_time(self) -> str:
        return str(
            self.entry.options.get(
                CONF_NOTIFICATION_TIME,
                DEFAULT_NOTIFICATION_TIME,
            )
        )

    @property
    def devices(self) -> list[dict[str, Any]]:
        raw = self.entry.options.get(CONF_NOTIFICATION_DEVICES, [])
        if not isinstance(raw, list):
            return []
        return [dict(item) for item in raw if isinstance(item, Mapping)]

    @property
    def enabled_devices(self) -> list[dict[str, Any]]:
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

    async def async_start(self) -> None:
        """Start notification listeners."""
        self._state = await self._store.async_load() or {}
        self._sync_target_repairs()
        self._unsub_coordinator = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )

        if self.mode != NOTIFICATION_MODE_ON_PUBLICATION:
            hour, minute, second = self._parse_time(self.notification_time)
            self._unsub_time = async_track_time_change(
                self.hass,
                self._async_scheduled_time,
                hour=hour,
                minute=minute,
                second=second,
            )

        await self._async_evaluate_startup()

    async def async_stop(self) -> None:
        """Stop notification listeners."""
        if self._unsub_time is not None:
            self._unsub_time()
            self._unsub_time = None
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

    @staticmethod
    def _parse_time(value: str) -> tuple[int, int, int]:
        try:
            parts = [int(part) for part in value.split(":")]
        except ValueError:
            return 18, 0, 0
        if len(parts) == 2:
            parts.append(0)
        if len(parts) != 3:
            return 18, 0, 0
        hour, minute, second = parts
        if not 0 <= hour <= 23 or not 0 <= minute <= 59 or not 0 <= second <= 59:
            return 18, 0, 0
        return hour, minute, second

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
        """Return services already notified for the current target date."""
        if self._state.get("notified_for") != self._target_date():
            return set()
        services = self._state.get("notified_services", [])
        if not isinstance(services, list):
            return set()
        return {str(service) for service in services}

    def _enabled_service_names(self) -> set[str]:
        """Return currently enabled notify service names."""
        return {str(device[DEVICE_SERVICE]) for device in self.enabled_devices}

    def _already_notified(self) -> bool:
        enabled = self._enabled_service_names()
        return bool(enabled) and enabled.issubset(self._notified_services())

    def _pending_devices(self) -> list[dict[str, Any]]:
        """Return enabled devices which still need the current notification."""
        notified = self._notified_services()
        return [
            device
            for device in self.enabled_devices
            if str(device[DEVICE_SERVICE]) not in notified
        ]

    async def _async_save_state(self) -> None:
        await self._store.async_save(self._state)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync_target_repairs()
        self.hass.async_create_task(
            self._async_handle_coordinator_update(),
            "Ceny paliw GOV.PL powiadomienia po aktualizacji danych",
        )

    async def _async_handle_coordinator_update(self) -> None:
        if not self.enabled or not self.enabled_devices or self._already_notified():
            return

        target_date = self._target_date()
        waiting_for = self._state.get("waiting_for_date")
        if waiting_for and waiting_for != target_date:
            self._state.pop("waiting_for_date", None)
            await self._async_save_state()

        if self.mode == NOTIFICATION_MODE_ON_PUBLICATION:
            if self.coordinator.data.tomorrow is not None:
                await self._async_send_price_notification()
            return

        if self.mode == NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION:
            if (
                self._state.get("waiting_for_date") == target_date
                and self.coordinator.data.tomorrow is not None
            ):
                await self._async_send_price_notification()

    async def _async_scheduled_time(self, _now: datetime) -> None:
        if not self.enabled or not self.enabled_devices:
            return

        await self.coordinator.async_request_refresh()
        if not self.coordinator.last_update_success:
            return
        if self._already_notified():
            return

        if self.mode == NOTIFICATION_MODE_SCHEDULED:
            if self.coordinator.data.tomorrow is not None:
                await self._async_send_price_notification()
            else:
                await self._async_send_not_published_notification()
            return

        if self.mode == NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION:
            if self.coordinator.data.tomorrow is not None:
                await self._async_send_price_notification()
                return
            self._state["waiting_for_date"] = self._target_date()
            await self._async_save_state()

    async def _async_evaluate_startup(self) -> None:
        if not self.enabled or not self.enabled_devices or self._already_notified():
            return

        if self.mode == NOTIFICATION_MODE_ON_PUBLICATION:
            if self.coordinator.data.tomorrow is not None:
                await self._async_send_price_notification()
            return

        now = dt_util.now()
        hour, minute, second = self._parse_time(self.notification_time)
        scheduled_seconds = hour * 3600 + minute * 60 + second
        now_seconds = now.hour * 3600 + now.minute * 60 + now.second
        if now_seconds < scheduled_seconds:
            return

        if self.mode == NOTIFICATION_MODE_SCHEDULED:
            if self.coordinator.data.tomorrow is not None:
                await self._async_send_price_notification()
            else:
                await self._async_send_not_published_notification()
            return

        if self.mode == NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION:
            if self.coordinator.data.tomorrow is not None:
                await self._async_send_price_notification()
            else:
                self._state["waiting_for_date"] = self._target_date()
                await self._async_save_state()

    async def _async_mark_filtered_as_done(self) -> None:
        """Mark a date as handled when notification filters intentionally skip it."""
        target_date = self._target_date()
        self._state["notified_for"] = target_date
        self._state["notified_services"] = sorted(self._enabled_service_names())
        self._state.pop("waiting_for_date", None)
        self.last_send_status = "Pominięto zgodnie z filtrem zmian"
        await self._async_save_state()

    async def _async_send_price_notification(self) -> None:
        if not has_relevant_change(self.coordinator.data, self.entry.options):
            await self._async_mark_filtered_as_done()
            return
        title, message = build_notification_content(
            self.hass,
            self.coordinator.data,
            self.entry.options,
        )
        await self._async_send_to_enabled_devices(
            title,
            message,
            mark_notified=True,
        )

    async def _async_send_not_published_notification(self) -> None:
        title, message = build_notification_content(
            self.hass,
            self.coordinator.data,
            self.entry.options,
        )
        await self._async_send_to_enabled_devices(
            title,
            message,
            mark_notified=True,
        )

    async def async_send_now_to_all(self) -> int:
        """Send the current daily-format notification to all enabled phones."""
        self._sync_target_repairs()
        title, message = build_notification_content(
            self.hass,
            self.coordinator.data,
            self.entry.options,
        )
        return await self._async_send_to_enabled_devices(
            title,
            message,
            mark_notified=False,
        )

    async def _async_send_to_enabled_devices(
        self,
        title: str,
        message: str,
        *,
        mark_notified: bool,
    ) -> int:
        async with self._send_lock:
            devices = self._pending_devices() if mark_notified else self.enabled_devices
            if not devices:
                self.last_send_status = "Brak włączonych telefonów do wysyłki"
                return 0

            successful_services: set[str] = set()
            for device in devices:
                target = str(device[DEVICE_SERVICE])
                display_name = str(
                    device.get(DEVICE_NAME) or default_device_name(target)
                )
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
                    successful_services.add(target)

            self.last_send_at = dt_util.now()
            self.last_send_status = (
                f"Wysłano: {len(successful_services)}/{len(devices)}"
            )

            if not mark_notified or not successful_services:
                return len(successful_services)

            target_date = self._target_date()
            notified = self._notified_services()
            notified.update(successful_services)
            self._state["notified_for"] = target_date
            self._state["notified_services"] = sorted(notified)

            if self._enabled_service_names().issubset(notified):
                self._state.pop("waiting_for_date", None)
            elif self.mode == NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION:
                self._state["waiting_for_date"] = target_date
            await self._async_save_state()
            return len(successful_services)
