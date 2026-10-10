"""Per-phone fuel selectors for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTHOR,
    DEVICE_FUELS,
    DEVICE_NAME,
    DEVICE_SERVICE,
    DOMAIN,
    FUEL_SELECTION_OPTIONS,
    NAME,
    NEWS_URL,
)
from .phone_config import (
    async_update_device_options,
    configured_devices,
    default_device_name,
    fuel_selection_option,
    fuels_for_selection_option,
    get_device,
    phone_key,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one dashboard fuel selector per configured phone."""
    async_add_entities(
        PhoneNotificationFuelSelect(entry, str(device[DEVICE_SERVICE]))
        for device in configured_devices(entry.options)
        if device.get(DEVICE_SERVICE)
    )


class PhoneNotificationFuelSelect(SelectEntity):
    """Choose which fuels are included in one phone's notifications."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:gas-station"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(FUEL_SELECTION_OPTIONS)

    def __init__(self, entry: ConfigEntry, target: str) -> None:
        self.entry = entry
        self.target = target
        device = get_device(entry.options, target) or {}
        display_name = str(device.get(DEVICE_NAME) or default_device_name(target))
        self._attr_unique_id = f"{DOMAIN}_phone_{phone_key(target)}_fuels"
        self._attr_name = f"{display_name} paliwa w powiadomieniu"

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
    def current_option(self) -> str:
        """Return the current fuel combination."""
        device = get_device(self.entry.options, self.target) or {}
        return fuel_selection_option(device.get(DEVICE_FUELS))

    async def async_select_option(self, option: str) -> None:
        """Set the fuel combination for this phone."""
        if option not in FUEL_SELECTION_OPTIONS:
            raise ValueError(f"Nieobsługiwana kombinacja paliw: {option}")
        await async_update_device_options(
            self.hass,
            self.entry,
            self.target,
            {DEVICE_FUELS: fuels_for_selection_option(option)},
        )
        self.async_write_ha_state()
