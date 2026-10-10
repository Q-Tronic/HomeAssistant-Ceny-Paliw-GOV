"""Helpers for per-phone notification configuration."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_FUELS,
    CONF_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATION_FUELS,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_PHONE_NOTIFICATION_MODE,
    DEVICE_ENABLED,
    DEVICE_FUELS,
    DEVICE_NAME,
    DEVICE_NOTIFICATION_MODE,
    DEVICE_NOTIFICATION_TIME,
    DEVICE_SERVICE,
    FUEL_SELECTION_OPTIONS,
    FUELS,
    PHONE_NOTIFICATION_MODE_NAMES,
    PHONE_NOTIFICATION_MODES,
)


def default_device_name(target: str) -> str:
    """Build a readable default name from a mobile_app notify target."""
    service = target.removeprefix("notify.")
    service = service.removeprefix("mobile_app_")
    if not service:
        return target
    return service.replace("_", " ").strip().title()


def normalize_time_string(value: Any, fallback: str = DEFAULT_NOTIFICATION_TIME) -> str:
    """Normalize a Home Assistant time value to HH:MM:SS."""
    if isinstance(value, time):
        return value.replace(microsecond=0).isoformat()
    text = str(value or fallback).strip()
    parts = text.split(":")
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return fallback
    if len(numbers) == 2:
        numbers.append(0)
    if len(numbers) != 3:
        return fallback
    hour, minute, second = numbers
    if not 0 <= hour <= 23 or not 0 <= minute <= 59 or not 0 <= second <= 59:
        return fallback
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def time_from_string(value: Any) -> time:
    """Convert a stored notification time to datetime.time."""
    normalized = normalize_time_string(value)
    hour, minute, second = (int(part) for part in normalized.split(":"))
    return time(hour=hour, minute=minute, second=second)


def normalize_fuels(value: Any, fallback: Any = None) -> list[str]:
    """Return a valid, stable ordered list of selected fuels."""
    source = value
    if not isinstance(source, (list, tuple, set)):
        source = fallback if fallback is not None else DEFAULT_NOTIFICATION_FUELS
    selected = {str(item) for item in source if str(item) in FUELS}
    return [fuel for fuel in FUELS if fuel in selected] or list(DEFAULT_NOTIFICATION_FUELS)


def fuel_selection_option(fuels: Any) -> str:
    """Return the select entity option matching a fuel list."""
    normalized = tuple(normalize_fuels(fuels))
    for label, values in FUEL_SELECTION_OPTIONS.items():
        if tuple(values) == normalized:
            return label
    return "PB95 + PB98 + ON"


def fuels_for_selection_option(option: str) -> list[str]:
    """Return fuels represented by a select entity option."""
    return list(FUEL_SELECTION_OPTIONS.get(option, tuple(FUELS)))


def normalize_notification_mode(value: Any) -> str:
    """Return a supported per-phone notification delivery mode."""
    mode = str(value or DEFAULT_PHONE_NOTIFICATION_MODE).strip()
    if mode not in PHONE_NOTIFICATION_MODES:
        return DEFAULT_PHONE_NOTIFICATION_MODE
    return mode


def notification_mode_option(mode: Any) -> str:
    """Return the dashboard label for a stored notification mode."""
    return PHONE_NOTIFICATION_MODE_NAMES[normalize_notification_mode(mode)]


def notification_mode_for_option(option: str) -> str:
    """Return the stored notification mode represented by a dashboard label."""
    for mode, label in PHONE_NOTIFICATION_MODE_NAMES.items():
        if label == option:
            return mode
    return DEFAULT_PHONE_NOTIFICATION_MODE


def normalize_target_selection(value: Any) -> list[str]:
    """Normalize a select selector value to a stable list of notification targets."""
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, (list, tuple, set)):
        candidates = list(value)
    else:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        target = str(item).strip()
        if not target or target in seen:
            continue
        seen.add(target)
        result.append(target)
    return result


def normalize_device(
    device: Mapping[str, Any],
    *,
    fallback_time: str = DEFAULT_NOTIFICATION_TIME,
    fallback_fuels: Any = None,
) -> dict[str, Any] | None:
    """Normalize one configured phone record."""
    target = str(device.get(DEVICE_SERVICE, "")).strip()
    if not target:
        return None
    return {
        DEVICE_SERVICE: target,
        DEVICE_NAME: str(device.get(DEVICE_NAME) or default_device_name(target)).strip()
        or default_device_name(target),
        DEVICE_ENABLED: bool(device.get(DEVICE_ENABLED, True)),
        DEVICE_NOTIFICATION_TIME: normalize_time_string(
            device.get(DEVICE_NOTIFICATION_TIME), fallback_time
        ),
        DEVICE_NOTIFICATION_MODE: normalize_notification_mode(
            device.get(DEVICE_NOTIFICATION_MODE)
        ),
        DEVICE_FUELS: normalize_fuels(
            device.get(DEVICE_FUELS),
            fallback_fuels if fallback_fuels is not None else DEFAULT_NOTIFICATION_FUELS,
        ),
    }


def normalized_options(options: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize options and migrate v1.3.x phone settings in memory."""
    result = deepcopy(dict(options))
    fallback_time = normalize_time_string(
        result.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME)
    )
    fallback_fuels = normalize_fuels(
        result.get(CONF_NOTIFICATION_FUELS, DEFAULT_NOTIFICATION_FUELS)
    )
    raw_devices = result.get(CONF_NOTIFICATION_DEVICES, [])
    devices_by_target: dict[str, dict[str, Any]] = {}
    if isinstance(raw_devices, list):
        for item in raw_devices:
            if not isinstance(item, Mapping):
                continue
            normalized = normalize_device(
                item,
                fallback_time=fallback_time,
                fallback_fuels=fallback_fuels,
            )
            if normalized is not None:
                # A service target is the stable phone identifier throughout the
                # integration. Keep only one record per target and let the last
                # stored record win if legacy/corrupt options contain duplicates.
                devices_by_target[str(normalized[DEVICE_SERVICE])] = normalized
    result[CONF_NOTIFICATION_DEVICES] = list(devices_by_target.values())
    return result


def configured_devices(options: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return normalized configured phone records."""
    return list(normalized_options(options).get(CONF_NOTIFICATION_DEVICES, []))


def get_device(options: Mapping[str, Any], target: str) -> dict[str, Any] | None:
    """Return one normalized phone record."""
    for device in configured_devices(options):
        if device.get(DEVICE_SERVICE) == target:
            return device
    return None


def phone_key(target: str) -> str:
    """Return a stable entity unique-id fragment for one notification target."""
    return "".join(char if char.isalnum() else "_" for char in target.lower()).strip("_")


def phone_entity_unique_ids(target: str) -> set[str]:
    """Return all dashboard configuration entity unique IDs for a phone."""
    key = phone_key(target)
    return {
        f"ceny_paliw_gov_pl_phone_{key}_enabled",
        f"ceny_paliw_gov_pl_phone_{key}_time",
        f"ceny_paliw_gov_pl_phone_{key}_mode",
        f"ceny_paliw_gov_pl_phone_{key}_fuels",
        f"ceny_paliw_gov_pl_phone_{key}_send_now",
        f"ceny_paliw_gov_pl_phone_{key}_last_notification_status",
        f"ceny_paliw_gov_pl_phone_{key}_last_notification_at",
    }


async def async_update_device_options(
    hass: HomeAssistant,
    entry: ConfigEntry,
    target: str,
    updates: Mapping[str, Any],
) -> None:
    """Persist one phone configuration change without reloading the integration."""
    options = normalized_options(entry.options)
    devices = list(options.get(CONF_NOTIFICATION_DEVICES, []))
    changed = False
    for index, device in enumerate(devices):
        if device.get(DEVICE_SERVICE) != target:
            continue
        updated = dict(device)
        updated.update(dict(updates))
        normalized = normalize_device(updated)
        if normalized is None:
            return
        devices[index] = normalized
        changed = normalized != device
        break
    else:
        return

    if not changed:
        return

    options[CONF_NOTIFICATION_DEVICES] = devices
    hass.config_entries.async_update_entry(entry, options=options)

    runtime = getattr(entry, "runtime_data", None)
    notifications = getattr(runtime, "notifications", None)
    if notifications is not None:
        await notifications.async_options_changed()
