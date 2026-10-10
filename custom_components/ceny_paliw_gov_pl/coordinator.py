"""Data update coordinator for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FuelPriceApi, FuelPriceApiError, FuelPriceData, FuelPriceParseError
from .const import (
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    EVENT_PRICES_UPDATED,
    UPDATE_INTERVAL_MINUTES_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class FuelPriceCoordinator(DataUpdateCoordinator[FuelPriceData]):
    """Coordinate updates from gov.pl."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        try:
            interval_minutes = int(
                entry.data.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                )
            )
        except (TypeError, ValueError):
            interval_minutes = DEFAULT_UPDATE_INTERVAL_MINUTES
        if interval_minutes not in UPDATE_INTERVAL_MINUTES_OPTIONS:
            interval_minutes = DEFAULT_UPDATE_INTERVAL_MINUTES

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )
        self._api = FuelPriceApi(async_get_clientsession(hass))
        self._last_data_fingerprint: tuple[Any, ...] | None = None
        self.last_error_kind: str | None = None
        self.last_error_message: str | None = None
        self.last_successful_update: datetime | None = None

    @staticmethod
    def _period_fingerprint(period: Any) -> tuple[Any, ...] | None:
        if period is None:
            return None
        return (
            period.valid_from,
            period.valid_to,
            period.published_on,
            tuple(sorted(period.prices.items())),
            period.source_url,
        )

    def _fingerprint(self, data: FuelPriceData) -> tuple[Any, ...]:
        return (
            data.today_date,
            data.tomorrow_date,
            self._period_fingerprint(data.today),
            self._period_fingerprint(data.tomorrow),
        )

    def _fire_update_event(self, data: FuelPriceData) -> None:
        tomorrow_prices = (
            {fuel: float(price) for fuel, price in data.tomorrow.prices.items()}
            if data.tomorrow is not None
            else None
        )
        today_prices = (
            {fuel: float(price) for fuel, price in data.today.prices.items()}
            if data.today is not None
            else None
        )
        self.hass.bus.async_fire(
            EVENT_PRICES_UPDATED,
            {
                "today_date": data.today_date.isoformat(),
                "tomorrow_date": data.tomorrow_date.isoformat(),
                "today_prices": today_prices,
                "tomorrow_prices": tomorrow_prices,
                "tomorrow_source": (
                    data.tomorrow.source_url if data.tomorrow is not None else None
                ),
                "tomorrow_published_on": (
                    data.tomorrow.published_on.isoformat()
                    if data.tomorrow is not None and data.tomorrow.published_on
                    else None
                ),
            },
        )

    async def _async_update_data(self) -> FuelPriceData:
        """Fetch the latest fuel prices."""
        now = dt_util.now()
        try:
            data = await self._api.async_fetch(today=now.date(), now=now)
        except FuelPriceParseError as err:
            self.last_error_kind = "parser"
            self.last_error_message = str(err)
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "parser_error",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="parser_error",
                translation_placeholders={"error": str(err)},
            )
            raise UpdateFailed(str(err)) from err
        except FuelPriceApiError as err:
            self.last_error_kind = "download"
            self.last_error_message = str(err)
            raise UpdateFailed(str(err)) from err

        ir.async_delete_issue(self.hass, DOMAIN, "parser_error")
        self.last_error_kind = None
        self.last_error_message = None
        self.last_successful_update = now

        fingerprint = self._fingerprint(data)
        if self._last_data_fingerprint is not None and fingerprint != self._last_data_fingerprint:
            self._fire_update_event(data)
        self._last_data_fingerprint = fingerprint
        return data
