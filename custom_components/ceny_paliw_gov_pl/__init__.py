"""Ceny paliw GOV.PL integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import FuelPriceCoordinator
from .notifications import FuelPriceNotificationManager

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass(slots=True)
class FuelPricesRuntimeData:
    """Runtime data for the integration."""

    coordinator: FuelPriceCoordinator
    notifications: FuelPriceNotificationManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ceny paliw GOV.PL from a config entry."""
    coordinator = FuelPriceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    notifications = FuelPriceNotificationManager(hass, entry, coordinator)
    entry.runtime_data = FuelPricesRuntimeData(
        coordinator=coordinator,
        notifications=notifications,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await notifications.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime: FuelPricesRuntimeData = entry.runtime_data
    await runtime.notifications.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
