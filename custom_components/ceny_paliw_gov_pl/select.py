"""Per-phone selectors for Maksymalne Ceny Paliw GOV.PL."""

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
    DEVICE_NOTIFICATION_MODE,
    DEVICE_SERVICE,
    DOMAIN,
    FUEL_SELECTION_OPTIONS,
    NAME,
    NEWS_URL,
    PHONE_NOTIFICATION_MODE_NAMES,
    PHONE_NOTIFICATION_MODE_PUBLICATION,
    PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE,
    PHONE_NOTIFICATION_MODE_SCHEDULED,
)
from .phone_config import (
    async_update_device_options,
    configured_devices,
    default_device_name,
    fuel_selection_option,
    fuels_for_selection_option,
    get_device,
    notification_mode_for_option,
    notification_mode_option,
    normalize_notification_mode,
    phone_key,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up dashboard selectors for each configured phone."""
    entities: list[SelectEntity] = []
    for device in configured_devices(entry.options):
        target = device.get(DEVICE_SERVICE)
        if not target:
            continue
        target_text = str(target)
        entities.append(PhoneNotificationFuelSelect(entry, target_text))
        entities.append(PhoneNotificationModeSelect(entry, target_text))
    async_add_entities(entities)


class _PhoneSelectBase(SelectEntity):
    """Base class for phone configuration selectors."""

    _attr_has_entity_name = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry, target: str) -> None:
        self.entry = entry
        self.target = target
        device = get_device(entry.options, target) or {}
        self.display_name = str(device.get(DEVICE_NAME) or default_device_name(target))

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


class PhoneNotificationFuelSelect(_PhoneSelectBase):
    """Choose which fuels are included in one phone's notifications."""

    _attr_icon = "mdi:gas-station"
    _attr_options = list(FUEL_SELECTION_OPTIONS)

    def __init__(self, entry: ConfigEntry, target: str) -> None:
        super().__init__(entry, target)
        self._attr_unique_id = f"{DOMAIN}_phone_{phone_key(target)}_fuels"
        self._attr_name = f"{self.display_name} paliwa w powiadomieniu"

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


class PhoneNotificationModeSelect(_PhoneSelectBase):
    """Choose when automatic notifications are sent to one phone."""

    _attr_options = list(PHONE_NOTIFICATION_MODE_NAMES.values())

    def __init__(self, entry: ConfigEntry, target: str) -> None:
        super().__init__(entry, target)
        self._attr_unique_id = f"{DOMAIN}_phone_{phone_key(target)}_mode"
        self._attr_name = f"{self.display_name} tryb wysyłki powiadomień"

    @property
    def current_option(self) -> str:
        """Return the current delivery mode label."""
        device = get_device(self.entry.options, self.target) or {}
        return notification_mode_option(device.get(DEVICE_NOTIFICATION_MODE))

    @property
    def icon(self) -> str:
        """Return an icon matching the current delivery mode."""
        device = get_device(self.entry.options, self.target) or {}
        mode = normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))
        if mode == PHONE_NOTIFICATION_MODE_PUBLICATION:
            return "mdi:bell-ring-outline"
        if mode == PHONE_NOTIFICATION_MODE_PUBLICATION_CHANGE:
            return "mdi:swap-vertical-bold"
        if mode == PHONE_NOTIFICATION_MODE_SCHEDULED:
            return "mdi:clock-outline"
        return "mdi:bell-outline"

    async def async_select_option(self, option: str) -> None:
        """Set the notification delivery mode for this phone."""
        if option not in PHONE_NOTIFICATION_MODE_NAMES.values():
            raise ValueError(f"Nieobsługiwany tryb powiadomień: {option}")
        await async_update_device_options(
            self.hass,
            self.entry,
            self.target,
            {DEVICE_NOTIFICATION_MODE: notification_mode_for_option(option)},
        )
        self.async_write_ha_state()
