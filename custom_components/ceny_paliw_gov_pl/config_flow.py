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
    CONF_SELECTED_DEVICE,
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
    async_send_current_notification,
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
    """Manage notification options using a menu based interface."""

    def __init__(self) -> None:
        self._working_options: dict[str, Any] | None = None
        self._selected_target: str | None = None
        self._phone_status = ""

    def _ensure_working_options(self) -> dict[str, Any]:
        if self._working_options is None:
            self._working_options = dict(self.config_entry.options)
            self._working_options.setdefault(
                CONF_NOTIFICATIONS_ENABLED,
                DEFAULT_NOTIFICATIONS_ENABLED,
            )
            self._working_options.setdefault(
                CONF_NOTIFICATION_TIME,
                DEFAULT_NOTIFICATION_TIME,
            )
            self._working_options.setdefault(
                CONF_NOTIFICATION_MODE,
                DEFAULT_NOTIFICATION_MODE,
            )
            devices = self._working_options.get(CONF_NOTIFICATION_DEVICES, [])
            if not isinstance(devices, list):
                devices = []
            self._working_options[CONF_NOTIFICATION_DEVICES] = [
                dict(item) for item in devices if isinstance(item, dict)
            ]
        return self._working_options

    def _existing_devices(self) -> dict[str, dict[str, Any]]:
        options = self._ensure_working_options()
        raw = options.get(CONF_NOTIFICATION_DEVICES, [])
        result: dict[str, dict[str, Any]] = {}
        for item in raw:
            target = item.get(DEVICE_SERVICE)
            if isinstance(target, str):
                result[target] = dict(item)
        return result

    def _set_devices(self, devices: list[dict[str, Any]]) -> None:
        self._ensure_working_options()[CONF_NOTIFICATION_DEVICES] = devices

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

    def _configured_phone_options(self) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        for target, device in self._existing_devices().items():
            name = str(device.get(DEVICE_NAME) or default_device_name(target))
            enabled = bool(device.get(DEVICE_ENABLED, True))
            suffix = "" if enabled else " (wyłączony)"
            options.append(
                {
                    "value": target,
                    "label": f"{name}{suffix}",
                }
            )
        options.sort(key=lambda item: item["label"].casefold())
        return options

    def _selected_device(self) -> dict[str, Any] | None:
        if self._selected_target is None:
            return None
        return self._existing_devices().get(self._selected_target)

    def _update_selected_device(self, *, name: str, enabled: bool) -> None:
        if self._selected_target is None:
            return
        devices = self._existing_devices()
        devices[self._selected_target] = {
            DEVICE_SERVICE: self._selected_target,
            DEVICE_NAME: name,
            DEVICE_ENABLED: enabled,
        }
        self._set_devices(list(devices.values()))

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show the main options menu."""
        self._ensure_working_options()
        return self.async_show_menu(
            step_id="init",
            menu_options=["notification_settings", "phones", "save"],
        )

    async def async_step_notification_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure global notification settings."""
        options = self._ensure_working_options()

        if user_input is not None:
            options[CONF_NOTIFICATIONS_ENABLED] = bool(
                user_input.get(
                    CONF_NOTIFICATIONS_ENABLED,
                    DEFAULT_NOTIFICATIONS_ENABLED,
                )
            )
            options[CONF_NOTIFICATION_TIME] = str(
                user_input.get(CONF_NOTIFICATION_TIME, DEFAULT_NOTIFICATION_TIME)
            )
            options[CONF_NOTIFICATION_MODE] = str(
                user_input.get(CONF_NOTIFICATION_MODE, DEFAULT_NOTIFICATION_MODE)
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id="notification_settings",
            data_schema=probatio.Schema(
                {
                    probatio.Optional(
                        CONF_NOTIFICATIONS_ENABLED,
                        description={
                            "suggested_value": options.get(
                                CONF_NOTIFICATIONS_ENABLED,
                                DEFAULT_NOTIFICATIONS_ENABLED,
                            )
                        },
                    ): BooleanSelector(),
                    probatio.Optional(
                        CONF_NOTIFICATION_TIME,
                        description={
                            "suggested_value": options.get(
                                CONF_NOTIFICATION_TIME,
                                DEFAULT_NOTIFICATION_TIME,
                            )
                        },
                    ): TimeSelector(),
                    probatio.Optional(
                        CONF_NOTIFICATION_MODE,
                        description={
                            "suggested_value": options.get(
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
                }
            ),
        )

    async def async_step_phones(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show phone management menu."""
        devices = self._existing_devices()
        menu_options = ["phone_list"]
        if devices:
            menu_options.append("choose_phone")
        menu_options.append("init")
        return self.async_show_menu(
            step_id="phones",
            menu_options=menu_options,
            description_placeholders={"count": str(len(devices))},
        )

    async def async_step_phone_list(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Add or remove phones from the notification list."""
        devices = self._existing_devices()
        selected_targets = list(devices)

        if user_input is not None:
            selected_targets = list(user_input.get(CONF_NOTIFICATION_SERVICES, []))
            updated_devices: list[dict[str, Any]] = []
            for target in selected_targets:
                current = devices.get(target)
                if current is None:
                    current = {
                        DEVICE_SERVICE: target,
                        DEVICE_NAME: default_device_name(target),
                        DEVICE_ENABLED: True,
                    }
                updated_devices.append(dict(current))
            self._set_devices(updated_devices)
            if self._selected_target not in selected_targets:
                self._selected_target = None
            return await self.async_step_phones()

        return self.async_show_form(
            step_id="phone_list",
            data_schema=probatio.Schema(
                {
                    probatio.Optional(
                        CONF_NOTIFICATION_SERVICES,
                        description={"suggested_value": selected_targets},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=self._target_options(),
                            multiple=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_choose_phone(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Choose a phone to configure."""
        phone_options = self._configured_phone_options()
        if not phone_options:
            return await self.async_step_phones()

        if user_input is not None:
            target = str(user_input.get(CONF_SELECTED_DEVICE, ""))
            if target in self._existing_devices():
                self._selected_target = target
                self._phone_status = ""
                return await self.async_step_phone_menu()

        suggested = self._selected_target
        if suggested not in self._existing_devices():
            suggested = phone_options[0]["value"]

        return self.async_show_form(
            step_id="choose_phone",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_SELECTED_DEVICE,
                        description={"suggested_value": suggested},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=phone_options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_phone_menu(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show actions for one selected phone."""
        device = self._selected_device()
        if device is None or self._selected_target is None:
            return await self.async_step_choose_phone()

        name = str(device.get(DEVICE_NAME) or default_device_name(self._selected_target))
        enabled = bool(device.get(DEVICE_ENABLED, True))
        return self.async_show_menu(
            step_id="phone_menu",
            menu_options=[
                "phone_settings",
                "phone_test",
                "phone_send_now",
                "choose_phone",
                "phones",
            ],
            description_placeholders={
                "device": name,
                "target": self._selected_target,
                "enabled": "tak" if enabled else "nie",
                "status": self._phone_status or "-",
            },
        )

    async def async_step_phone_settings(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Edit one phone."""
        device = self._selected_device()
        if device is None or self._selected_target is None:
            return await self.async_step_choose_phone()

        default_name = str(
            device.get(DEVICE_NAME) or default_device_name(self._selected_target)
        )
        default_enabled = bool(device.get(DEVICE_ENABLED, True))

        if user_input is not None:
            display_name = str(user_input.get(CONF_DEVICE_NAME) or default_name).strip()
            if not display_name:
                display_name = default_device_name(self._selected_target)
            enabled = bool(user_input.get(CONF_DEVICE_ENABLED, True))
            self._update_selected_device(name=display_name, enabled=enabled)
            self._phone_status = "✓"
            return await self.async_step_phone_menu()

        return self.async_show_form(
            step_id="phone_settings",
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
                }
            ),
            description_placeholders={
                "device": default_name,
                "target": self._selected_target,
            },
        )

    async def async_step_phone_test(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Immediately send a test notification to the selected phone."""
        device = self._selected_device()
        if device is None or self._selected_target is None:
            return await self.async_step_choose_phone()

        display_name = str(
            device.get(DEVICE_NAME) or default_device_name(self._selected_target)
        )
        try:
            await async_send_test_notification(
                self.hass,
                self._selected_target,
                display_name,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Nie udało się wysłać testowego powiadomienia na %s",
                self._selected_target,
            )
            self._phone_status = "⚠"
        else:
            self._phone_status = "✓"
        return await self.async_step_phone_menu()

    async def async_step_phone_send_now(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Immediately send the normal daily notification to the selected phone."""
        device = self._selected_device()
        if device is None or self._selected_target is None:
            return await self.async_step_choose_phone()

        try:
            runtime_data = self.config_entry.runtime_data
            coordinator = runtime_data.coordinator
            await coordinator.async_request_refresh()
            await async_send_current_notification(
                self.hass,
                self._selected_target,
                coordinator.data,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Nie udało się wysłać bieżącego powiadomienia na %s",
                self._selected_target,
            )
            self._phone_status = "⚠"
        else:
            self._phone_status = "✓"
        return await self.async_step_phone_menu()

    async def async_step_save(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Save all changes and reload the integration."""
        return self.async_create_entry(
            title="",
            data=self._ensure_working_options(),
        )
