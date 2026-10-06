"""Diagnostics support for Ceny paliw GOV.PL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import PricePeriod
from .const import (
    CONF_NOTIFICATION_CUSTOM_MESSAGE,
    CONF_NOTIFICATION_CUSTOM_TITLE,
    CONF_NOTIFICATION_FUELS,
    CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_ONLY_ON_CHANGE,
    CONF_NOTIFICATION_TIME,
    CONF_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFICATION_FUELS,
    DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
    DEFAULT_NOTIFICATION_MODE,
    DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATIONS_ENABLED,
    EVENT_PRICES_UPDATED,
    FUELS,
    HISTORY_PERIODS,
    VERSION,
)


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


def _summary_as_dict(summary: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in summary.items():
        result[key] = float(value) if isinstance(value, Decimal) else value
    return result


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    history = runtime.history
    notifications = runtime.notifications
    data = coordinator.data

    history_summaries: dict[str, Any] = {}
    for fuel in FUELS:
        history_summaries[fuel] = {
            str(days): _summary_as_dict(
                history.summary(fuel, days, data.today_date)
            )
            for days in HISTORY_PERIODS
        }

    return {
        "integration_version": VERSION,
        "today_date": data.today_date.isoformat(),
        "tomorrow_date": data.tomorrow_date.isoformat(),
        "today": _period_as_dict(data.today),
        "tomorrow": _period_as_dict(data.tomorrow),
        "fetched_at": data.fetched_at.isoformat(),
        "parsed_periods": data.parsed_periods,
        "last_update_success": coordinator.last_update_success,
        "last_successful_update": (
            coordinator.last_successful_update.isoformat()
            if coordinator.last_successful_update
            else None
        ),
        "last_error_kind": coordinator.last_error_kind,
        "last_error_message": coordinator.last_error_message,
        "event_name": EVENT_PRICES_UPDATED,
        "history": {
            "stored_records": len(history.records),
            "summaries": history_summaries,
        },
        "notifications": {
            "enabled": bool(
                entry.options.get(
                    CONF_NOTIFICATIONS_ENABLED,
                    DEFAULT_NOTIFICATIONS_ENABLED,
                )
            ),
            "time": entry.options.get(
                CONF_NOTIFICATION_TIME,
                DEFAULT_NOTIFICATION_TIME,
            ),
            "mode": entry.options.get(
                CONF_NOTIFICATION_MODE,
                DEFAULT_NOTIFICATION_MODE,
            ),
            "fuels": entry.options.get(
                CONF_NOTIFICATION_FUELS,
                list(DEFAULT_NOTIFICATION_FUELS),
            ),
            "only_on_change": bool(
                entry.options.get(
                    CONF_NOTIFICATION_ONLY_ON_CHANGE,
                    DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
                )
            ),
            "minimum_change_grosz": entry.options.get(
                CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
                DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
            ),
            "custom_title_configured": bool(
                str(entry.options.get(CONF_NOTIFICATION_CUSTOM_TITLE, "")).strip()
            ),
            "custom_message_configured": bool(
                str(entry.options.get(CONF_NOTIFICATION_CUSTOM_MESSAGE, "")).strip()
            ),
            "missing_enabled_targets": notifications.missing_enabled_targets,
            "last_send_status": notifications.last_send_status,
            "last_send_at": (
                notifications.last_send_at.isoformat()
                if notifications.last_send_at
                else None
            ),
            "devices": [
                {
                    "service": device.get("service"),
                    "name": device.get("name"),
                    "enabled": device.get("enabled", True),
                }
                for device in entry.options.get("notification_devices", [])
                if isinstance(device, dict)
            ],
        },
    }
