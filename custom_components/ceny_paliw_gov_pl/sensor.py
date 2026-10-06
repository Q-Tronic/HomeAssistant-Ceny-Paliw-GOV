"""Sensors for Ceny paliw GOV.PL."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Literal

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FuelPriceData, PricePeriod
from .const import (
    AUTHOR,
    DOMAIN,
    FUEL_NAMES,
    FUEL_ON,
    FUEL_PB95,
    FUEL_PB98,
    NAME,
    NEWS_URL,
    STATUS_NO_CHANGE,
    STATUS_NOT_PUBLISHED,
    UNIT_PRICE,
)
from .coordinator import FuelPriceCoordinator

DayKind = Literal["today", "tomorrow"]
SensorKind = Literal["price", "change"]


@dataclass(frozen=True, kw_only=True)
class FuelSensorDescription(SensorEntityDescription):
    """Describe a fuel price sensor."""

    fuel: str
    kind: SensorKind
    day: DayKind | None = None


SENSORS: tuple[FuelSensorDescription, ...] = (
    FuelSensorDescription(
        key="pb95_today",
        name="Cena PB95 dzisiaj",
        icon="mdi:gas-station",
        suggested_display_precision=2,
        fuel=FUEL_PB95,
        kind="price",
        day="today",
    ),
    FuelSensorDescription(
        key="pb95_tomorrow",
        name="Cena PB95 jutro",
        icon="mdi:gas-station",
        suggested_display_precision=2,
        fuel=FUEL_PB95,
        kind="price",
        day="tomorrow",
    ),
    FuelSensorDescription(
        key="pb95_change",
        name="PB95 zmiana ceny",
        icon="mdi:swap-vertical",
        fuel=FUEL_PB95,
        kind="change",
    ),
    FuelSensorDescription(
        key="pb98_today",
        name="Cena PB98 dzisiaj",
        icon="mdi:gas-station",
        suggested_display_precision=2,
        fuel=FUEL_PB98,
        kind="price",
        day="today",
    ),
    FuelSensorDescription(
        key="pb98_tomorrow",
        name="Cena PB98 jutro",
        icon="mdi:gas-station",
        suggested_display_precision=2,
        fuel=FUEL_PB98,
        kind="price",
        day="tomorrow",
    ),
    FuelSensorDescription(
        key="pb98_change",
        name="PB98 zmiana ceny",
        icon="mdi:swap-vertical",
        fuel=FUEL_PB98,
        kind="change",
    ),
    FuelSensorDescription(
        key="on_today",
        name="Cena ON dzisiaj",
        icon="mdi:gas-station",
        suggested_display_precision=2,
        fuel=FUEL_ON,
        kind="price",
        day="today",
    ),
    FuelSensorDescription(
        key="on_tomorrow",
        name="Cena ON jutro",
        icon="mdi:gas-station",
        suggested_display_precision=2,
        fuel=FUEL_ON,
        kind="price",
        day="tomorrow",
    ),
    FuelSensorDescription(
        key="on_change",
        name="ON zmiana ceny",
        icon="mdi:swap-vertical",
        fuel=FUEL_ON,
        kind="change",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up fuel price sensors from a config entry."""
    coordinator: FuelPriceCoordinator = entry.runtime_data
    async_add_entities(
        FuelPriceSensor(coordinator, description) for description in SENSORS
    )


class FuelPriceSensor(CoordinatorEntity[FuelPriceCoordinator], SensorEntity):
    """Representation of one fuel price sensor."""

    entity_description: FuelSensorDescription
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: FuelPriceCoordinator,
        description: FuelSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_name = description.name

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

    @property
    def native_value(self) -> str | float:
        """Return the sensor state."""
        if self.entity_description.kind == "change":
            return self._change_state()

        period = self._period_for_day(self.entity_description.day)
        if period is None:
            return STATUS_NOT_PUBLISHED

        value = period.prices.get(self.entity_description.fuel)
        if value is None:
            return STATUS_NOT_PUBLISHED
        return float(value)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return price unit only when the state is numeric."""
        if self.entity_description.kind != "price":
            return None
        period = self._period_for_day(self.entity_description.day)
        if period is None:
            return None
        if self.entity_description.fuel not in period.prices:
            return None
        return UNIT_PRICE

    @property
    def icon(self) -> str | None:
        """Return a context-sensitive icon."""
        if self.entity_description.kind != "change":
            return self.entity_description.icon

        difference = self._difference()
        if difference is None:
            return "mdi:help-circle-outline"
        if difference > 0:
            return "mdi:trending-up"
        if difference < 0:
            return "mdi:trending-down"
        return "mdi:trending-neutral"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful source and comparison attributes."""
        if self.entity_description.kind == "change":
            return self._change_attributes()

        period = self._period_for_day(self.entity_description.day)
        expected_date = (
            self.coordinator.data.today_date
            if self.entity_description.day == "today"
            else self.coordinator.data.tomorrow_date
        )

        attributes: dict[str, Any] = {
            "paliwo": FUEL_NAMES[self.entity_description.fuel],
            "oczekiwana_data": expected_date.isoformat(),
            "status_danych": (
                "opublikowano" if period is not None else "nie_opublikowano"
            ),
            "ostatnia_aktualizacja": self.coordinator.data.fetched_at.isoformat(),
        }
        if period is None:
            attributes["zrodlo"] = NEWS_URL
            return attributes

        value = period.prices.get(self.entity_description.fuel)
        attributes.update(
            {
                "cena_numeryczna": float(value) if value is not None else None,
                "data_obowiazywania_od": period.valid_from.isoformat(),
                "data_obowiazywania_do": period.valid_to.isoformat(),
                "data_publikacji": (
                    period.published_on.isoformat() if period.published_on else None
                ),
                "zrodlo": period.source_url,
            }
        )
        return attributes

    def _period_for_day(self, day: DayKind | None) -> PricePeriod | None:
        if day == "today":
            return self.coordinator.data.today
        if day == "tomorrow":
            return self.coordinator.data.tomorrow
        return None

    def _difference(self) -> Decimal | None:
        data: FuelPriceData = self.coordinator.data
        if data.today is None or data.tomorrow is None:
            return None

        today = data.today.prices.get(self.entity_description.fuel)
        tomorrow = data.tomorrow.prices.get(self.entity_description.fuel)
        if today is None or tomorrow is None:
            return None
        return (tomorrow - today).quantize(Decimal("0.01"))

    def _difference_grosz(self) -> int | None:
        difference = self._difference()
        if difference is None:
            return None
        return int(
            (difference * Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

    def _change_state(self) -> str:
        grosz = self._difference_grosz()
        if grosz is None:
            return STATUS_NOT_PUBLISHED
        if grosz > 0:
            return f"drożej o {grosz}gr"
        if grosz < 0:
            return f"taniej o {abs(grosz)}gr"
        return STATUS_NO_CHANGE

    def _change_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        today_period = data.today
        tomorrow_period = data.tomorrow
        difference = self._difference()
        grosz = self._difference_grosz()

        today_price = (
            today_period.prices.get(self.entity_description.fuel)
            if today_period
            else None
        )
        tomorrow_price = (
            tomorrow_period.prices.get(self.entity_description.fuel)
            if tomorrow_period
            else None
        )

        if grosz is None:
            direction = "nie_opublikowano"
        elif grosz > 0:
            direction = "drozej"
        elif grosz < 0:
            direction = "taniej"
        else:
            direction = "bez_zmian"

        return {
            "paliwo": FUEL_NAMES[self.entity_description.fuel],
            "cena_dzis": float(today_price) if today_price is not None else None,
            "cena_jutro": float(tomorrow_price) if tomorrow_price is not None else None,
            "roznica_zl": float(difference) if difference is not None else None,
            "roznica_gr": grosz,
            "kierunek": direction,
            "data_dzis": data.today_date.isoformat(),
            "data_jutro": data.tomorrow_date.isoformat(),
            "zrodlo_dzis": today_period.source_url if today_period else NEWS_URL,
            "zrodlo_jutro": tomorrow_period.source_url if tomorrow_period else NEWS_URL,
            "ostatnia_aktualizacja": data.fetched_at.isoformat(),
        }
