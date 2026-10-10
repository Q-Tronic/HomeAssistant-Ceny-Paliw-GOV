"""Maksymalne Ceny Paliw GOV.PL integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, NAME
from .coordinator import FuelPriceCoordinator
from .history import FuelPriceHistoryManager
from .notifications import FuelPriceNotificationManager
from .phone_config import (
    configured_devices,
    normalized_options,
    phone_entity_unique_ids,
)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.TIME,
    Platform.SELECT,
]


@dataclass(slots=True)
class FuelPricesRuntimeData:
    """Runtime data for the integration."""

    coordinator: FuelPriceCoordinator
    history: FuelPriceHistoryManager
    notifications: FuelPriceNotificationManager
    phone_targets: frozenset[str]



def _configured_phone_targets(entry: ConfigEntry) -> frozenset[str]:
    """Return the configured notify targets that need dashboard entities."""
    return frozenset(
        str(device.get("service", ""))
        for device in configured_devices(entry.options)
        if device.get("service")
    )


async def _async_options_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload only when phones are added or removed."""
    runtime: FuelPricesRuntimeData = entry.runtime_data
    current_targets = _configured_phone_targets(entry)
    if current_targets != runtime.phone_targets:
        await hass.config_entries.async_reload(entry.entry_id)


def _cleanup_removed_phone_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove dashboard configuration entities for phones removed by the administrator."""
    allowed: set[str] = set()
    for device in configured_devices(entry.options):
        target = str(device.get("service", ""))
        if target:
            allowed.update(phone_entity_unique_ids(target))

    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = entity_entry.unique_id
        if not unique_id.startswith(f"{DOMAIN}_phone_"):
            continue
        if unique_id not in allowed:
            registry.async_remove(entity_entry.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Maksymalne Ceny Paliw GOV.PL from a config entry."""
    normalized = normalized_options(entry.options)
    updates: dict[str, object] = {}
    if normalized != dict(entry.options):
        updates["options"] = normalized
    if entry.title != NAME:
        updates["title"] = NAME
    if updates:
        hass.config_entries.async_update_entry(entry, **updates)

    _cleanup_removed_phone_entities(hass, entry)

    coordinator = FuelPriceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    history = FuelPriceHistoryManager(hass, entry, coordinator)
    await history.async_start()

    notifications = FuelPriceNotificationManager(hass, entry, coordinator)
    entry.runtime_data = FuelPricesRuntimeData(
        coordinator=coordinator,
        history=history,
        notifications=notifications,
        phone_targets=_configured_phone_targets(entry),
    )
    entry.async_on_unload(entry.add_update_listener(_async_options_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await notifications.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime: FuelPricesRuntimeData = entry.runtime_data
    await runtime.notifications.async_stop()
    await runtime.history.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
