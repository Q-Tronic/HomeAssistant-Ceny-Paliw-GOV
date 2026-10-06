"""Config flow for Ceny paliw GOV.PL."""

from __future__ import annotations

import logging
from typing import Any

import probatio

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)

from .const import (
    CONF_DEVICE_ENABLED,
    CONF_DEVICE_NAME,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_MODE,
    CONF_NOTIFICATION_SERVICES,
    CONF_NOTIFICATION_TIME,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_TEST_NOTIFICATION,
    DEFAULT_NOTIFICATION_MODE,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_NOTIFICATIONS_ENABLED,
    DEVICE_ENABLED,
    DEVICE_NAME,
    DEVICE_SERVICE,
    DOMAIN,
    NAME,
    NOTIFICATION_MODES,
)
from .notifications import (
    async_send_test_notification,
    default_device_name,
    mobile_app_notify_targets,
)

_LOGGER = logging.getLogger(__name__)


class FuelPricesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ceny paliw GOV.PL."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(step_id="user", data_schema=probatio.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return FuelPricesOptionsFlow()


class FuelPricesOptionsFlow(config_entries.OptionsFlowWithReload):
    """Manage notification options."""

    def __init__(self) -> None:
        self._pending_options: dict[str, Any] = {}
        self._selected_services: list[str] = []
        self._device_index = 0
        self._devices: list[dict[str, Any]] = []

    def _existing_devices(self) -> dict[str, dict[str, Any]]:
        raw = self.config_entry.options.get(CONF_NOTIFICATION_DEVICES, [])
        result: dict[str, dict[str, Any]] = {}
        if not isinstance(raw, list):
            return result
        for item in raw:
            if not isinstance(item, dict):
                continue
            target = item.get(DEVICE_SERVICE)
            if isinstance(target, str):
                result[target] = dict(item)
        return result

    def _target_options(self) -> list[dict[str, str]]:
        options = mobile_app_notify_targets(self.hass)
        known = {option["value"] for option in options}
        for target, device in self._existing_devices().items():
            if target in known:
                continue
            name = str(device.get(DEVICE_NAME) or default_device_name(target))
            options.append(
                {
                    "value": target,
                    "label": f"{name} ({target}, obecnie niedostępne)",
                }
            )
        options.sort(key=lambda item: item["label"].casefold())
        return options

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure global notification settings and selected phones."""
        existing_devices = self._existing_devices()
        existing_targets = list(existing_devices)

        if user_input is not None:
            self._selected_services = list(
                user_input.get(CONF_NOTIFICATION_SERVICES, [])
            )
            self._pending_options = {
                CONF_NOTIFICATIONS_ENABLED: bool(
                    user_input.get(
                        CONF_NOTIFICATIONS_ENABLED,
                        DEFAULT_NOTIFICATIONS_ENABLED,
                    )
                ),
                CONF_NOTIFICATION_TIME: str(
                    user_input.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME)
                ),
                CONF_NOTIFICATION_MODE: str(
                    user_input.get(CONF_NOTIFICATION_MODE, DEFAULT_NOTIFICATION_MODE)
                ),
            }
            self._devices = []
            self._device_index = 0

            if not self._selected_services:
                self._pending_options[CONF_NOTIFICATION_DEVICES] = []
                return self.async_create_entry(title="", data=self._pending_options)

            return await self.async_step_device()

        target_options = self._target_options()
        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Optional(
                        CONF_NOTIFICATIONS_ENABLED,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_NOTIFICATIONS_ENABLED,
                                DEFAULT_NOTIFICATIONS_ENABLED,
                            )
                        },
                    ): BooleanSelector(),
                    probatio.Optional(
                        CONF_NOTIFICATION_TIME,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_NOTIFICATION_TIME,
                                DEFAULT_NOTIFICATION_TIME,
                            )
                        },
                    ): TimeSelector(),
                    probatio.Optional(
                        CONF_NOTIFICATION_MODE,
                        description={
                            "suggested_value": self.config_entry.options.get(
                                CONF_NOTIFICATION_MODE,
                                DEFAULT_NOTIFICATION_MODE,
                            )
                        },
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(NOTIFICATION_MODES),
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key="notification_mode",
                        )
                    ),
                    probatio.Optional(
                        CONF_NOTIFICATION_SERVICES,
                        description={"suggested_value": existing_targets},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=target_options,
                            multiple=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_device(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure one phone at a time."""
        target = self._selected_services[self._device_index]
        existing = self._existing_devices().get(target, {})
        default_name = str(existing.get(DEVICE_NAME) or default_device_name(target))
        default_enabled = bool(existing.get(DEVICE_ENABLED, True))
        errors: dict[str, str] = {}

        if user_input is not None:
            display_name = str(user_input.get(CONF_DEVICE_NAME) or default_name).strip()
            if not display_name:
                display_name = default_device_name(target)
            enabled = bool(user_input.get(CONF_DEVICE_ENABLED, True))

            if user_input.get(CONF_TEST_NOTIFICATION, False):
                try:
                    await async_send_test_notification(
                        self.hass,
                        target,
                        display_name,
                    )
                except Exception:  # noqa: BLE001
                    _LOGGER.exception(
                        "Nie udało się wysłać testowego powiadomienia na %s",
                        target,
                    )
                    errors["base"] = "test_notification_failed"

            if errors:
                default_name = display_name
                default_enabled = enabled

            if not errors:
                self._devices.append(
                    {
                        DEVICE_SERVICE: target,
                        DEVICE_NAME: display_name,
                        DEVICE_ENABLED: enabled,
                    }
                )
                self._device_index += 1
                if self._device_index < len(self._selected_services):
                    return await self.async_step_device()

                self._pending_options[CONF_NOTIFICATION_DEVICES] = self._devices
                return self.async_create_entry(title="", data=self._pending_options)

        return self.async_show_form(
            step_id="device",
            data_schema=probatio.Schema(
                {
                    probatio.Optional(
                        CONF_DEVICE_NAME,
                        description={"suggested_value": default_name},
                    ): TextSelector(),
                    probatio.Optional(
                        CONF_DEVICE_ENABLED,
                        description={"suggested_value": default_enabled},
                    ): BooleanSelector(),
                    probatio.Optional(
                        CONF_TEST_NOTIFICATION,
                        description={"suggested_value": False},
                    ): BooleanSelector(),
                }
            ),
            errors=errors,
            description_placeholders={
                "device": default_name,
                "target": target,
                "position": str(self._device_index + 1),
                "count": str(len(self._selected_services)),
            },
        )
