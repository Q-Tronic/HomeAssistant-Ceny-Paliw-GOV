"""Button entities for Ceny paliw GOV.PL."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import AUTHOR, DOMAIN, NAME, NEWS_URL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up action buttons."""
    async_add_entities(
        [
            FuelPricesRefreshButton(entry),
            FuelPricesSendAllButton(entry),
        ]
    )


class FuelPricesBaseButton(ButtonEntity):
    """Base integration button."""

    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name=NAME,
            manufacturer=AUTHOR,
            model="Maksymalne ceny detaliczne paliw",
            configuration_url=NEWS_URL,
        )


class FuelPricesRefreshButton(FuelPricesBaseButton):
    """Force an immediate gov.pl refresh."""

    _attr_name = "Sprawdź ceny teraz"
    _attr_icon = "mdi:refresh"
    _attr_unique_id = f"{DOMAIN}_refresh_now"

    async def async_press(self) -> None:
        """Refresh fuel prices immediately."""
        await self.entry.runtime_data.coordinator.async_request_refresh()


class FuelPricesSendAllButton(FuelPricesBaseButton):
    """Send current daily notification to all enabled phones."""

    _attr_name = "Wyślij wszystkim teraz"
    _attr_icon = "mdi:send"
    _attr_unique_id = f"{DOMAIN}_send_all_now"

    async def async_press(self) -> None:
        """Refresh data and send current notification."""
        runtime = self.entry.runtime_data
        await runtime.coordinator.async_request_refresh()
        if not runtime.coordinator.last_update_success:
            raise RuntimeError("Nie udało się odświeżyć cen przed wysyłką")
        await runtime.notifications.async_send_now_to_all()
