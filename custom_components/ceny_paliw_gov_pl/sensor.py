"""Sensor platform for Ceny paliw GOV.PL."""

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
from homeassistant.util import dt as dt_util

from .api import FuelPriceData, PricePeriod
from .const import (
    AUTHOR,
    DOMAIN,
    EVENT_PRICES_UPDATED,
    FUEL_NAMES,
    FUEL_ON,
    FUEL_PB95,
    FUEL_PB98,
    FUELS,
    HISTORY_PERIODS,
    NAME,
    NEWS_URL,
    STALE_DATA_AFTER,
    STATUS_DOWNLOAD_ERROR,
    STATUS_NO_CHANGE,
    STATUS_NO_HISTORY,
    STATUS_NOT_PUBLISHED,
    STATUS_PUBLISHED,
    STATUS_STALE,
    STATUS_WAITING,
    UNIT_PRICE,
    VERSION,
)
from .coordinator import FuelPriceCoordinator
from .history import FuelPriceHistoryManager

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
    runtime = entry.runtime_data
    coordinator: FuelPriceCoordinator = runtime.coordinator
    history: FuelPriceHistoryManager = runtime.history

    entities: list[SensorEntity] = [
        FuelPriceSensor(coordinator, description) for description in SENSORS
    ]
    entities.append(FuelPricesStatusSensor(entry, coordinator))
    entities.extend(
        FuelHistoryAverageSensor(coordinator, history, fuel, days)
        for fuel in FUELS
        for days in HISTORY_PERIODS
    )
    async_add_entities(entities)


class FuelEntityBase:
    """Shared device info."""

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


class FuelPriceSensor(
    FuelEntityBase,
    CoordinatorEntity[FuelPriceCoordinator],
    SensorEntity,
):
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
            trend = "not_published"
        elif grosz > 0:
            direction = "drozej"
            trend = "up"
        elif grosz < 0:
            direction = "taniej"
            trend = "down"
        else:
            direction = "bez_zmian"
            trend = "equal"

        percent: Decimal | None = None
        if difference is not None and today_price not in (None, Decimal("0")):
            percent = ((difference / today_price) * Decimal("100")).quantize(
                Decimal("0.01")
            )

        return {
            "paliwo": FUEL_NAMES[self.entity_description.fuel],
            "cena_dzis": float(today_price) if today_price is not None else None,
            "cena_jutro": float(tomorrow_price) if tomorrow_price is not None else None,
            "roznica_zl": float(difference) if difference is not None else None,
            "roznica_gr": grosz,
            "roznica_procent": float(percent) if percent is not None else None,
            "kierunek": direction,
            "trend": trend,
            "data_dzis": data.today_date.isoformat(),
            "data_jutro": data.tomorrow_date.isoformat(),
            "data_publikacji_jutro": (
                tomorrow_period.published_on.isoformat()
                if tomorrow_period and tomorrow_period.published_on
                else None
            ),
            "zrodlo_dzis": today_period.source_url if today_period else NEWS_URL,
            "zrodlo_jutro": tomorrow_period.source_url if tomorrow_period else NEWS_URL,
            "ostatnia_aktualizacja": data.fetched_at.isoformat(),
        }


class FuelPricesStatusSensor(
    FuelEntityBase,
    CoordinatorEntity[FuelPriceCoordinator],
    SensorEntity,
):
    """Integration status sensor that remains readable after update failures."""

    _attr_has_entity_name = False
    _attr_name = "Status publikacji cen paliw"
    _attr_unique_id = f"{DOMAIN}_status"
    _attr_icon = "mdi:information-outline"

    def __init__(self, entry: ConfigEntry, coordinator: FuelPriceCoordinator) -> None:
        super().__init__(coordinator)
        self.entry = entry

    @property
    def available(self) -> bool:
        """Keep the status sensor available even after a failed refresh."""
        return True

    @property
    def native_value(self) -> str:
        if not self.coordinator.last_update_success:
            return STATUS_DOWNLOAD_ERROR
        data = self.coordinator.data
        if dt_util.now() - data.fetched_at > STALE_DATA_AFTER:
            return STATUS_STALE
        if data.tomorrow is not None:
            return STATUS_PUBLISHED
        return STATUS_WAITING

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        runtime = self.entry.runtime_data
        return {
            "wersja_integracji": VERSION,
            "data_dzis": data.today_date.isoformat(),
            "data_jutro": data.tomorrow_date.isoformat(),
            "jutro_opublikowane": data.tomorrow is not None,
            "ostatnie_pobranie": data.fetched_at.isoformat(),
            "ostatnia_udana_aktualizacja": (
                self.coordinator.last_successful_update.isoformat()
                if self.coordinator.last_successful_update
                else data.fetched_at.isoformat()
            ),
            "ostatni_blad": self.coordinator.last_error_message,
            "typ_ostatniego_bledu": self.coordinator.last_error_kind,
            "znalezione_publikacje": data.parsed_periods,
            "brakujace_cele_powiadomien": runtime.notifications.missing_enabled_targets,
            "zdarzenie_aktualizacji": EVENT_PRICES_UPDATED,
            "zrodlo": NEWS_URL,
        }


class FuelHistoryAverageSensor(
    FuelEntityBase,
    CoordinatorEntity[FuelPriceCoordinator],
    SensorEntity,
):
    """Average price and statistics for a local history window."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:chart-line"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: FuelPriceCoordinator,
        history: FuelPriceHistoryManager,
        fuel: str,
        days: int,
    ) -> None:
        super().__init__(coordinator)
        self.history = history
        self.fuel = fuel
        self.days = days
        self._attr_unique_id = f"{DOMAIN}_{fuel}_average_{days}d"
        self._attr_name = f"Średnia {FUEL_NAMES[fuel]} {days} dni"

    def _summary(self) -> dict[str, Any]:
        return self.history.summary(
            self.fuel,
            self.days,
            self.coordinator.data.today_date,
        )

    @property
    def native_value(self) -> float | str:
        summary = self._summary()
        average = summary["average"]
        if average is None:
            return STATUS_NO_HISTORY
        return float(average)

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UNIT_PRICE if self._summary()["average"] is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        summary = self._summary()

        def number(value: Any) -> float | None:
            return float(value) if isinstance(value, Decimal) else None

        return {
            "paliwo": FUEL_NAMES[self.fuel],
            "okres_dni": self.days,
            "liczba_probek": summary["samples"],
            "minimum": number(summary["minimum"]),
            "maksimum": number(summary["maximum"]),
            "pierwsza_cena": number(summary["first"]),
            "ostatnia_cena": number(summary["last"]),
            "zmiana_zl": number(summary["change"]),
            "zmiana_procent": number(summary["change_percent"]),
            "zapisane_dni_lacznie": self.history.available_days(
                self.fuel,
                self.coordinator.data.today_date,
            ),
            "historia_lokalna": True,
        }
