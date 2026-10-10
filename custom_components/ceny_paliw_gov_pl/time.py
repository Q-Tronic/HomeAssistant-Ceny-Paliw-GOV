"""Per-phone notification time entities for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTHOR,
    DEVICE_NAME,
    DEVICE_NOTIFICATION_TIME,
    DEVICE_SERVICE,
    DOMAIN,
    NAME,
    NEWS_URL,
)
from .phone_config import (
    async_update_device_options,
    configured_devices,
    default_device_name,
    get_device,
    phone_key,
    time_from_string,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one dashboard notification time per configured phone."""
    async_add_entities(
        PhoneNotificationTime(entry, str(device[DEVICE_SERVICE]))
        for device in configured_devices(entry.options)
        if device.get(DEVICE_SERVICE)
    )


class PhoneNotificationTime(TimeEntity):
    """Configure the daily notification time for one phone."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:clock-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry, target: str) -> None:
        self.entry = entry
        self.target = target
        device = get_device(entry.options, target) or {}
        display_name = str(device.get(DEVICE_NAME) or default_device_name(target))
        self._attr_unique_id = f"{DOMAIN}_phone_{phone_key(target)}_time"
        self._attr_name = f"{display_name} godzina powiadomienia"

    @property
    def device_info(self) -> DeviceInfo:
        """Return integration device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name=NAME,
            manufacturer=AUTHOR,
            model="Maksymalne ceny detaliczne paliw",
            configuration_url=NEWS_URL,
        )

    @property
    def native_value(self) -> time:
        """Return configured daily notification time."""
        device = get_device(self.entry.options, self.target) or {}
        return time_from_string(device.get(DEVICE_NOTIFICATION_TIME))

    async def async_set_value(self, value: time) -> None:
        """Set the daily notification time for this phone."""
        await async_update_device_options(
            self.hass,
            self.entry,
            self.target,
            {DEVICE_NOTIFICATION_TIME: value.replace(microsecond=0).isoformat()},
        )
        self.async_write_ha_state()
