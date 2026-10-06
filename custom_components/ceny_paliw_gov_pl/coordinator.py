"""Data update coordinator for Ceny paliw GOV.PL."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FuelPriceApi, FuelPriceApiError, FuelPriceData
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class FuelPriceCoordinator(DataUpdateCoordinator[FuelPriceData]):
    """Coordinate updates from gov.pl."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._api = FuelPriceApi(async_get_clientsession(hass))

    async def _async_update_data(self) -> FuelPriceData:
        """Fetch the latest fuel prices."""
        now = dt_util.now()
        try:
            return await self._api.async_fetch(today=now.date(), now=now)
        except FuelPriceApiError as err:
            raise UpdateFailed(str(err)) from err
