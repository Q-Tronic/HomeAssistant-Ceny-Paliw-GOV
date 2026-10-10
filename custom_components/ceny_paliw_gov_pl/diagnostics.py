"""Diagnostics support for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data

from .api import PricePeriod
from .const import (
    CONF_NOTIFICATION_CUSTOM_MESSAGE,
    CONF_NOTIFICATION_CUSTOM_TITLE,
    CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
    CONF_NOTIFICATION_ONLY_ON_CHANGE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
    DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEVICE_ENABLED,
    DEVICE_FUELS,
    DEVICE_NAME,
    DEVICE_NOTIFICATION_TIME,
    DEVICE_SERVICE,
    EVENT_PRICES_UPDATED,
    FUELS,
    HISTORY_PERIODS,
    VERSION,
)
from .phone_config import configured_devices

_DIAGNOSTIC_PHONE_REDACTIONS = {DEVICE_SERVICE, DEVICE_NAME}


def _period_as_dict(period: PricePeriod | None) -> dict[str, Any] | None:
    """Convert a price period into diagnostics-safe data."""
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
    """Convert Decimal values in a history summary."""
    result: dict[str, Any] = {}
    for key, value in summary.items():
        result[key] = float(value) if isinstance(value, Decimal) else value
    return result


def _phone_diagnostics(device: dict[str, Any], notifications: Any) -> dict[str, Any]:
    """Build diagnostics for one phone without exposing its identity."""
    target = str(device.get(DEVICE_SERVICE, ""))
    raw = {
        "service": target,
        "name": device.get(DEVICE_NAME),
        "enabled": device.get(DEVICE_ENABLED, True),
        "notification_time": device.get(DEVICE_NOTIFICATION_TIME),
        "fuels": device.get(DEVICE_FUELS),
        "last_notification_status": notifications.phone_status(target),
        "last_notification_at": (
            notifications.phone_last_sent_at(target).isoformat()
            if notifications.phone_last_sent_at(target)
            else None
        ),
        "waiting_for_publication": notifications.phone_waiting(target),
    }
    return async_redact_data(raw, _DIAGNOSTIC_PHONE_REDACTIONS)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry without personal phone identifiers."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    history = runtime.history
    notifications = runtime.notifications
    data = coordinator.data

    history_summaries: dict[str, Any] = {}
    for fuel in FUELS:
        history_summaries[fuel] = {
            str(days): _summary_as_dict(history.summary(fuel, days, data.today_date))
            for days in HISTORY_PERIODS
        }

    return {
        "integration_version": VERSION,
        "update_interval_minutes": entry.data.get(
            CONF_UPDATE_INTERVAL_MINUTES,
            DEFAULT_UPDATE_INTERVAL_MINUTES,
        ),
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
            "missing_enabled_targets_count": len(notifications.missing_enabled_targets),
            "last_send_status": notifications.last_send_status,
            "last_send_at": (
                notifications.last_send_at.isoformat()
                if notifications.last_send_at
                else None
            ),
            "devices": [
                _phone_diagnostics(device, notifications)
                for device in configured_devices(entry.options)
            ],
        },
    }
