"""Diagnostics support for Ceny paliw GOV.PL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import PricePeriod
from .coordinator import FuelPriceCoordinator


def _period_as_dict(period: PricePeriod | None) -> dict[str, Any] | None:
    if period is None:
        return None
    return {
        "valid_from": period.valid_from.isoformat(),
        "valid_to": period.valid_to.isoformat(),
        "published_on": period.published_on.isoformat() if period.published_on else None,
        "prices": {
            fuel: float(value) if isinstance(value, Decimal) else value
            for fuel, value in period.prices.items()
        },
        "source_url": period.source_url,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: FuelPriceCoordinator = entry.runtime_data
    data = coordinator.data
    return {
        "today_date": data.today_date.isoformat(),
        "tomorrow_date": data.tomorrow_date.isoformat(),
        "today": _period_as_dict(data.today),
        "tomorrow": _period_as_dict(data.tomorrow),
        "fetched_at": data.fetched_at.isoformat(),
        "parsed_periods": data.parsed_periods,
        "last_update_success": coordinator.last_update_success,
    }
