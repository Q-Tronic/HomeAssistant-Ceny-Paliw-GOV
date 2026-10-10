"""Per-phone notification switches for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTHOR,
    DEVICE_ENABLED,
    DEVICE_NAME,
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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one dashboard notification switch per configured phone."""
    async_add_entities(
        PhoneNotificationSwitch(entry, str(device[DEVICE_SERVICE]))
        for device in configured_devices(entry.options)
        if device.get(DEVICE_SERVICE)
    )


class PhoneNotificationSwitch(SwitchEntity):
    """Enable or disable automatic fuel-price notifications for one phone."""

    _attr_has_entity_name = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry, target: str) -> None:
        self.entry = entry
        self.target = target
        device = get_device(entry.options, target) or {}
        display_name = str(device.get(DEVICE_NAME) or default_device_name(target))
        self._attr_unique_id = f"{DOMAIN}_phone_{phone_key(target)}_enabled"
        self._attr_name = f"{display_name} powiadomienia"

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
    def is_on(self) -> bool:
        """Return whether automatic notifications are enabled for this phone."""
        device = get_device(self.entry.options, self.target)
        return bool(device and device.get(DEVICE_ENABLED, True))

    @property
    def icon(self) -> str:
        """Return an icon reflecting the current notification state."""
        return "mdi:bell-ring-outline" if self.is_on else "mdi:bell-off-outline"

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable automatic notifications for this phone."""
        await async_update_device_options(
            self.hass,
            self.entry,
            self.target,
            {DEVICE_ENABLED: True},
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable automatic notifications for this phone."""
        await async_update_device_options(
            self.hass,
            self.entry,
            self.target,
            {DEVICE_ENABLED: False},
        )
        self.async_write_ha_state()
