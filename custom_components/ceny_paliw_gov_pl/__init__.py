"""Maksymalne Ceny Paliw GOV.PL integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    NAME,
    HISTORY_STORAGE_KEY_PREFIX,
    HISTORY_STORAGE_VERSION,
    NOTIFICATION_STORAGE_KEY_PREFIX,
    NOTIFICATION_STORAGE_VERSION,
)
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
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await notifications.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    runtime: FuelPricesRuntimeData = entry.runtime_data
    await runtime.notifications.async_stop()
    await runtime.history.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove local data when the user deletes the integration."""
    await Store(
        hass,
        NOTIFICATION_STORAGE_VERSION,
        f"{NOTIFICATION_STORAGE_KEY_PREFIX}.{entry.entry_id}",
    ).async_remove()
    await Store(
        hass,
        HISTORY_STORAGE_VERSION,
        f"{HISTORY_STORAGE_KEY_PREFIX}.{entry.entry_id}",
    ).async_remove()
    ir.async_delete_issue(hass, DOMAIN, "parser_error")
