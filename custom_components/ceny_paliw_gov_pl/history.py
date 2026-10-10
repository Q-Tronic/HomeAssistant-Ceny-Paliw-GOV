"""Local fuel price history for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .api import FuelPriceData, PricePeriod
from .const import (
    FUELS,
    HISTORY_RETENTION_DAYS,
    HISTORY_STORAGE_KEY_PREFIX,
    HISTORY_STORAGE_VERSION,
)
from .coordinator import FuelPriceCoordinator

_LOGGER = logging.getLogger(__name__)


class FuelPriceHistoryManager:
    """Keep a compact local daily price history."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: FuelPriceCoordinator,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(
            hass,
            HISTORY_STORAGE_VERSION,
            f"{HISTORY_STORAGE_KEY_PREFIX}.{entry.entry_id}",
        )
        self._records: dict[str, dict[str, Any]] = {}
        self._unsub_coordinator: CALLBACK_TYPE | None = None

    @property
    def records(self) -> dict[str, dict[str, Any]]:
        """Return a copy of history records."""
        return {day: dict(record) for day, record in self._records.items()}

    async def async_start(self) -> None:
        """Load stored history and start recording updates."""
        stored = await self._store.async_load() or {}
        raw_records = stored.get("records", {})
        if isinstance(raw_records, dict):
            self._records = {
                str(day): dict(record)
                for day, record in raw_records.items()
                if isinstance(record, dict)
            }
        self._record_data(self.coordinator.data)
        await self._async_save()
        self._unsub_coordinator = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )

    async def async_stop(self) -> None:
        """Stop history listener and persist data."""
        if self._unsub_coordinator is not None:
            self._unsub_coordinator()
            self._unsub_coordinator = None
        await self._async_save()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Record new data before entity listeners render states."""
        if not self.coordinator.last_update_success:
            return
        self._record_data(self.coordinator.data)
        self.hass.async_create_task(
            self._async_save(),
            "Maksymalne Ceny Paliw GOV.PL zapis historii",
        )

    def _record_data(self, data: FuelPriceData) -> None:
        """Record all parsed price periods available on the news page."""
        periods: Iterable[PricePeriod] = data.periods
        if not periods:
            periods = tuple(
                period for period in (data.today, data.tomorrow) if period is not None
            )

        # The parser orders periods from newest publication to oldest. Record
        # them in the opposite order so a newer corrected publication wins when
        # validity ranges overlap.
        for period in reversed(tuple(periods)):
            self._record_period(period)

        cutoff = data.today_date - timedelta(days=HISTORY_RETENTION_DAYS)
        future_cutoff = data.today_date + timedelta(days=31)
        self._records = {
            day: record
            for day, record in self._records.items()
            if cutoff <= self._parse_date(day) <= future_cutoff
        }

    def _record_period(self, period: PricePeriod) -> None:
        """Expand one validity period into daily records."""
        span = (period.valid_to - period.valid_from).days
        if span < 0 or span > 31:
            _LOGGER.warning(
                "Pomijam nietypowy zakres cen %s - %s",
                period.valid_from,
                period.valid_to,
            )
            return

        for offset in range(span + 1):
            day = period.valid_from + timedelta(days=offset)
            self._records[day.isoformat()] = {
                "prices": {
                    fuel: float(period.prices[fuel])
                    for fuel in FUELS
                    if fuel in period.prices
                },
                "source_url": period.source_url,
                "published_on": (
                    period.published_on.isoformat() if period.published_on else None
                ),
                "valid_from": period.valid_from.isoformat(),
                "valid_to": period.valid_to.isoformat(),
            }

    @staticmethod
    def _parse_date(value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return date.min

    async def _async_save(self) -> None:
        await self._store.async_save({"records": self._records})

    def price(self, fuel: str, day: date) -> Decimal | None:
        """Return a recorded price for an exact day."""
        record = self._records.get(day.isoformat())
        if not record:
            return None
        prices = record.get("prices", {})
        if not isinstance(prices, dict) or fuel not in prices:
            return None
        try:
            return Decimal(str(prices[fuel])).quantize(Decimal("0.01"))
        except Exception:  # noqa: BLE001
            return None

    def prices_in_window(self, fuel: str, days: int, end_day: date) -> list[Decimal]:
        """Return daily prices from a calendar-day window."""
        if days <= 0:
            return []
        start_day = end_day - timedelta(days=days - 1)
        values: list[Decimal] = []
        current = start_day
        while current <= end_day:
            value = self.price(fuel, current)
            if value is not None:
                values.append(value)
            current += timedelta(days=1)
        return values

    def summary(self, fuel: str, days: int, end_day: date) -> dict[str, Any]:
        """Return summary statistics for a history window."""
        values = self.prices_in_window(fuel, days, end_day)
        if not values:
            return {
                "days": days,
                "samples": 0,
                "average": None,
                "minimum": None,
                "maximum": None,
                "first": None,
                "last": None,
                "change": None,
                "change_percent": None,
            }

        average = (sum(values) / Decimal(len(values))).quantize(Decimal("0.01"))
        first = values[0]
        last = values[-1]
        change = (last - first).quantize(Decimal("0.01"))
        change_percent: Decimal | None = None
        if first != 0:
            change_percent = ((change / first) * Decimal("100")).quantize(
                Decimal("0.01")
            )

        return {
            "days": days,
            "samples": len(values),
            "average": average,
            "minimum": min(values),
            "maximum": max(values),
            "first": first,
            "last": last,
            "change": change,
            "change_percent": change_percent,
        }

    def available_days(self, fuel: str, end_day: date | None = None) -> int:
        """Return number of stored daily samples for one fuel."""
        count = 0
        for day, record in self._records.items():
            parsed_day = self._parse_date(day)
            if end_day is not None and parsed_day > end_day:
                continue
            prices = record.get("prices", {})
            if isinstance(prices, dict) and fuel in prices:
                count += 1
        return count
