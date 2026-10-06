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
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import FuelPriceData, PricePeriod
from .const import (
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_TIME,
    CONF_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFICATION_MODE,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEVICE_ENABLED,
    DEVICE_NAME,
    DEVICE_SERVICE,
    FUEL_NAMES,
    FUELS,
    NOTIFICATION_DATA,
    NOTIFICATION_MODE_ON_PUBLICATION,
    NOTIFICATION_MODE_SCHEDULED,
    NOTIFICATION_MODE_SCHEDULED_THEN_PUBLICATION,
    NOTIFICATION_TEST_TITLE,
    NOTIFICATION_TITLE,
    STATUS_NO_CHANGE,
    STATUS_NOT_PUBLISHED,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
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


def _format_price(value: Decimal | None) -> str:
    if value is None:
        return STATUS_NOT_PUBLISHED
    return f"{value:.2f}".replace(".", ",") + f" {UNIT_PRICE}"


def _price(period: PricePeriod | None, fuel: str) -> Decimal | None:
    if period is None:
        return None
    return period.prices.get(fuel)


def _difference_grosz(
    today_period: PricePeriod | None,
    tomorrow_period: PricePeriod | None,
    fuel: str,
) -> int | None:
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
    grosz = _difference_grosz(today_period, tomorrow_period, fuel)
    if grosz is None:
        return STATUS_NOT_PUBLISHED
    if grosz > 0:
        return f"drożej o {grosz}gr"
    if grosz < 0:
        return f"taniej o {abs(grosz)}gr"
    return STATUS_NO_CHANGE


def build_price_notification(data: FuelPriceData) -> str:
    """Build the notification body with today, tomorrow and price changes."""
    date_text = data.tomorrow_date.strftime("%d.%m.%Y")
    lines = [f"Ceny paliw na jutro, {date_text}", ""]

    for fuel in FUELS:
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


async def async_send_mobile_notification(
    hass: HomeAssistant,
    target: str,
    title: str,
    message: str,
) -> None:
    """Send a high priority mobile_app notification."""
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
        f"Urządzenie: {display_name}\n"
        "Tryb wysyłki: ttl 0, priority high."
    )
    await async_send_mobile_notification(
        hass,
        target,
        NOTIFICATION_TEST_TITLE,
        message,
    )


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
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{entry.entry_id}",
        )
        self._state: dict[str, Any] = {}
        self._unsub_time: CALLBACK_TYPE | None = None
        self._unsub_coordinator: CALLBACK_TYPE | None = None
        self._send_lock = asyncio.Lock()

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

    async def async_start(self) -> None:
        """Start notification listeners."""
        self._state = await self._store.async_load() or {}
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

    async def _async_send_price_notification(self) -> None:
        await self._async_send_to_enabled_devices(
            NOTIFICATION_TITLE,
            build_price_notification(self.coordinator.data),
            mark_notified=True,
        )

    async def _async_send_not_published_notification(self) -> None:
        await self._async_send_to_enabled_devices(
            NOTIFICATION_TITLE,
            build_not_published_notification(self.coordinator.data),
            mark_notified=True,
        )

    async def _async_send_to_enabled_devices(
        self,
        title: str,
        message: str,
        *,
        mark_notified: bool,
    ) -> None:
        async with self._send_lock:
            devices = self._pending_devices() if mark_notified else self.enabled_devices
            if not devices:
                return

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

            if not mark_notified or not successful_services:
                return

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
