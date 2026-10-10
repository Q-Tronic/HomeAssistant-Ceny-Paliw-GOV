"""Binary sensors for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import AUTHOR, DOMAIN, FUEL_NAMES, FUELS, NAME, NEWS_URL
from .coordinator import FuelPriceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up tomorrow-more-expensive binary sensors."""
    coordinator: FuelPriceCoordinator = entry.runtime_data.coordinator
    async_add_entities(FuelMoreExpensiveBinarySensor(coordinator, fuel) for fuel in FUELS)


class FuelMoreExpensiveBinarySensor(
    CoordinatorEntity[FuelPriceCoordinator], BinarySensorEntity
):
    """Indicate whether a fuel will be more expensive tomorrow."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: FuelPriceCoordinator, fuel: str) -> None:
        super().__init__(coordinator)
        self.fuel = fuel
        self._attr_unique_id = f"{DOMAIN}_{fuel}_tomorrow_more_expensive"
        self._attr_name = f"{FUEL_NAMES[fuel]} jutro drożej"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name=NAME,
            manufacturer=AUTHOR,
            model="Maksymalne ceny detaliczne paliw",
            configuration_url=NEWS_URL,
        )

    def _difference(self) -> Decimal | None:
        data = self.coordinator.data
        if data.today is None or data.tomorrow is None:
            return None
        today = data.today.prices.get(self.fuel)
        tomorrow = data.tomorrow.prices.get(self.fuel)
        if today is None or tomorrow is None:
            return None
        return (tomorrow - today).quantize(Decimal("0.01"))

    @property
    def is_on(self) -> bool | None:
        """Return unknown when one of the compared prices is missing."""
        difference = self._difference()
        return None if difference is None else difference > 0

    @property
    def icon(self) -> str:
        """Return an icon matching the current price trend."""
        difference = self._difference()
        if difference is None:
            return "mdi:cash-question"
        if difference > 0:
            return "mdi:cash-plus"
        if difference < 0:
            return "mdi:cash-minus"
        return "mdi:cash-check"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        difference = self._difference()
        data = self.coordinator.data
        grosz = None
        if difference is not None:
            grosz = int(
                (difference * Decimal("100")).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
        return {
            "paliwo": FUEL_NAMES[self.fuel],
            "dane_opublikowane": data.tomorrow is not None,
            "roznica_zl": float(difference) if difference is not None else None,
            "roznica_gr": grosz,
            "data_jutro": data.tomorrow_date.isoformat(),
        }
