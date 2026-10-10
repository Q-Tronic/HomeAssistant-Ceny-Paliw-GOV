"""Config flow for Maksymalne Ceny Paliw GOV.PL."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TimeSelector,
)

from .const import (
    CONF_DEVICE_ENABLED,
    CONF_DEVICE_NAME,
    CONF_DEVICE_NOTIFICATION_FUELS,
    CONF_DEVICE_NOTIFICATION_MODE,
    CONF_DEVICE_NOTIFICATION_TIME,
    CONF_NOTIFICATION_CUSTOM_MESSAGE,
    CONF_NOTIFICATION_CUSTOM_TITLE,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
    CONF_NOTIFICATION_ONLY_ON_CHANGE,
    CONF_NOTIFICATION_SERVICES,
    CONF_SELECTED_DEVICE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_NOTIFICATION_CUSTOM_MESSAGE,
    DEFAULT_NOTIFICATION_CUSTOM_TITLE,
    DEFAULT_NOTIFICATION_FUELS,
    DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
    DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
    DEFAULT_NOTIFICATION_TIME,
    DEFAULT_PHONE_NOTIFICATION_MODE,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DEVICE_ENABLED,
    DEVICE_FUELS,
    DEVICE_NAME,
    DEVICE_NOTIFICATION_MODE,
    DEVICE_NOTIFICATION_TIME,
    DEVICE_SERVICE,
    DOMAIN,
    FUEL_NAMES,
    FUELS,
    NAME,
    PHONE_NOTIFICATION_MODE_NAMES,
    UNIT_GROSZ,
    UPDATE_INTERVAL_MINUTES_OPTIONS,
)
from .notifications import (
    async_send_test_notification,
    mobile_app_notify_targets,
)
from .phone_config import (
    default_device_name,
    merge_working_options,
    normalize_fuels,
    normalize_notification_mode,
    normalize_target_selection,
    normalize_time_string,
    normalized_options,
)

_LOGGER = logging.getLogger(__name__)


class FuelPricesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Maksymalne Ceny Paliw GOV.PL."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title=NAME,
                data={CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES},
            )

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Reconfigure integration-level source polling settings."""
        entry = self._get_reconfigure_entry()
        try:
            current_interval = int(
                entry.data.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                )
            )
        except (TypeError, ValueError):
            current_interval = DEFAULT_UPDATE_INTERVAL_MINUTES
        if current_interval not in UPDATE_INTERVAL_MINUTES_OPTIONS:
            current_interval = DEFAULT_UPDATE_INTERVAL_MINUTES

        if user_input is not None:
            try:
                interval = int(
                    user_input.get(
                        CONF_UPDATE_INTERVAL_MINUTES,
                        DEFAULT_UPDATE_INTERVAL_MINUTES,
                    )
                )
            except (TypeError, ValueError):
                interval = DEFAULT_UPDATE_INTERVAL_MINUTES
            if interval not in UPDATE_INTERVAL_MINUTES_OPTIONS:
                interval = DEFAULT_UPDATE_INTERVAL_MINUTES
            return self.async_update_reload_and_abort(
                entry,
                data_updates={CONF_UPDATE_INTERVAL_MINUTES: interval},
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL_MINUTES,
                        description={"suggested_value": str(current_interval)},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": str(value), "label": f"{value} min"}
                                for value in UPDATE_INTERVAL_MINUTES_OPTIONS
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return FuelPricesOptionsFlow()


class FuelPricesOptionsFlow(config_entries.OptionsFlowWithReload):
    """Manage integration options using a menu based interface."""

    def __init__(self) -> None:
        self._working_options: dict[str, Any] | None = None
        self._base_options: dict[str, Any] | None = None
        self._selected_target: str | None = None
        self._phone_status = ""
        self._diagnostic_status = ""

    def _ensure_working_options(self) -> dict[str, Any]:
        if self._working_options is None:
            self._base_options = dict(self.config_entry.options)
            self._working_options = normalized_options(self._base_options)
            defaults: dict[str, Any] = {
                CONF_NOTIFICATION_ONLY_ON_CHANGE: DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
                CONF_NOTIFICATION_MIN_CHANGE_GROSZ: DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
                CONF_NOTIFICATION_CUSTOM_TITLE: DEFAULT_NOTIFICATION_CUSTOM_TITLE,
                CONF_NOTIFICATION_CUSTOM_MESSAGE: DEFAULT_NOTIFICATION_CUSTOM_MESSAGE,
            }
            for key, value in defaults.items():
                self._working_options.setdefault(key, value)
        return self._working_options

    def _existing_devices(self) -> dict[str, dict[str, Any]]:
        options = self._ensure_working_options()
        raw = options.get(CONF_NOTIFICATION_DEVICES, [])
        result: dict[str, dict[str, Any]] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
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
            options.append({"value": target, "label": f"{name}{suffix}"})
        options.sort(key=lambda item: item["label"].casefold())
        return options

    def _selected_device(self) -> dict[str, Any] | None:
        if self._selected_target is None:
            return None
        return self._existing_devices().get(self._selected_target)

    def _update_selected_device(
        self,
        *,
        name: str,
        enabled: bool,
        notification_time: Any,
        notification_mode: Any,
        fuels: Any,
    ) -> None:
        if self._selected_target is None:
            return
        devices = self._existing_devices()
        devices[self._selected_target] = {
            DEVICE_SERVICE: self._selected_target,
            DEVICE_NAME: name,
            DEVICE_ENABLED: enabled,
            DEVICE_NOTIFICATION_TIME: normalize_time_string(notification_time),
            DEVICE_NOTIFICATION_MODE: normalize_notification_mode(notification_mode),
            DEVICE_FUELS: normalize_fuels(fuels),
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
            menu_options=[
                "phones",
                "notification_content",
                "notification_filters",
                "diagnostics",
                "save",
            ],
        )

    async def async_step_notification_content(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure optional global notification templates."""
        options = self._ensure_working_options()
        if user_input is not None:
            options[CONF_NOTIFICATION_CUSTOM_TITLE] = str(
                user_input.get(CONF_NOTIFICATION_CUSTOM_TITLE, "") or ""
            )
            options[CONF_NOTIFICATION_CUSTOM_MESSAGE] = str(
                user_input.get(CONF_NOTIFICATION_CUSTOM_MESSAGE, "") or ""
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id="notification_content",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NOTIFICATION_CUSTOM_TITLE,
                        description={
                            "suggested_value": options.get(
                                CONF_NOTIFICATION_CUSTOM_TITLE,
                                DEFAULT_NOTIFICATION_CUSTOM_TITLE,
                            )
                        },
                    ): TemplateSelector(),
                    vol.Optional(
                        CONF_NOTIFICATION_CUSTOM_MESSAGE,
                        description={
                            "suggested_value": options.get(
                                CONF_NOTIFICATION_CUSTOM_MESSAGE,
                                DEFAULT_NOTIFICATION_CUSTOM_MESSAGE,
                            )
                        },
                    ): TemplateSelector(),
                }
            ),
        )

    async def async_step_notification_filters(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure global change based notification filters."""
        options = self._ensure_working_options()
        if user_input is not None:
            options[CONF_NOTIFICATION_ONLY_ON_CHANGE] = bool(
                user_input.get(
                    CONF_NOTIFICATION_ONLY_ON_CHANGE,
                    DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
                )
            )
            options[CONF_NOTIFICATION_MIN_CHANGE_GROSZ] = int(
                float(
                    user_input.get(
                        CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
                        DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
                    )
                )
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id="notification_filters",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NOTIFICATION_ONLY_ON_CHANGE,
                        description={
                            "suggested_value": options.get(
                                CONF_NOTIFICATION_ONLY_ON_CHANGE,
                                DEFAULT_NOTIFICATION_ONLY_ON_CHANGE,
                            )
                        },
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
                        description={
                            "suggested_value": options.get(
                                CONF_NOTIFICATION_MIN_CHANGE_GROSZ,
                                DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ,
                            )
                        },
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=100,
                            step=1,
                            unit_of_measurement=UNIT_GROSZ,
                            mode=NumberSelectorMode.BOX,
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
            requested_targets = normalize_target_selection(
                user_input.get(CONF_NOTIFICATION_SERVICES)
            )
            allowed_targets = {option["value"] for option in self._target_options()}
            selected_targets = [
                target for target in requested_targets if target in allowed_targets
            ]
            updated_devices: list[dict[str, Any]] = []
            for target in selected_targets:
                current = devices.get(target)
                if current is None:
                    current = {
                        DEVICE_SERVICE: target,
                        DEVICE_NAME: default_device_name(target),
                        DEVICE_ENABLED: True,
                        DEVICE_NOTIFICATION_TIME: DEFAULT_NOTIFICATION_TIME,
                        DEVICE_NOTIFICATION_MODE: DEFAULT_PHONE_NOTIFICATION_MODE,
                        DEVICE_FUELS: list(DEFAULT_NOTIFICATION_FUELS),
                    }
                updated_devices.append(dict(current))
            self._set_devices(updated_devices)
            if self._selected_target not in selected_targets:
                self._selected_target = None
            return await self.async_step_phones()

        return self.async_show_form(
            step_id="phone_list",
            data_schema=vol.Schema(
                {
                    vol.Optional(
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
            data_schema=vol.Schema(
                {
                    vol.Required(
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
        notification_time = normalize_time_string(device.get(DEVICE_NOTIFICATION_TIME))
        notification_mode = PHONE_NOTIFICATION_MODE_NAMES[
            normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))
        ]
        fuels = ", ".join(
            FUEL_NAMES[fuel] for fuel in normalize_fuels(device.get(DEVICE_FUELS))
        )
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
                "time": notification_time[:5],
                "mode": notification_mode,
                "fuels": fuels,
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
        default_time = normalize_time_string(device.get(DEVICE_NOTIFICATION_TIME))
        default_mode = normalize_notification_mode(device.get(DEVICE_NOTIFICATION_MODE))
        default_fuels = normalize_fuels(device.get(DEVICE_FUELS))

        if user_input is not None:
            display_name = str(user_input.get(CONF_DEVICE_NAME) or default_name).strip()
            if not display_name:
                display_name = default_device_name(self._selected_target)
            enabled = bool(user_input.get(CONF_DEVICE_ENABLED, True))
            notification_time = user_input.get(
                CONF_DEVICE_NOTIFICATION_TIME,
                default_time,
            )
            notification_mode = user_input.get(
                CONF_DEVICE_NOTIFICATION_MODE,
                default_mode,
            )
            fuels = user_input.get(CONF_DEVICE_NOTIFICATION_FUELS, default_fuels)
            self._update_selected_device(
                name=display_name,
                enabled=enabled,
                notification_time=notification_time,
                notification_mode=notification_mode,
                fuels=fuels,
            )
            self._phone_status = "Zapisano"
            return await self.async_step_phone_menu()

        fuel_options = [
            {"value": fuel, "label": FUEL_NAMES[fuel]} for fuel in FUELS
        ]
        return self.async_show_form(
            step_id="phone_settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICE_NAME,
                        description={"suggested_value": default_name},
                    ): TextSelector(),
                    vol.Optional(
                        CONF_DEVICE_ENABLED,
                        description={"suggested_value": default_enabled},
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_DEVICE_NOTIFICATION_TIME,
                        description={"suggested_value": default_time},
                    ): TimeSelector(),
                    vol.Optional(
                        CONF_DEVICE_NOTIFICATION_MODE,
                        description={"suggested_value": default_mode},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": mode, "label": label}
                                for mode, label in PHONE_NOTIFICATION_MODE_NAMES.items()
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_DEVICE_NOTIFICATION_FUELS,
                        description={"suggested_value": default_fuels},
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=fuel_options,
                            multiple=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
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
            self._phone_status = "Błąd wysyłki"
        else:
            self._phone_status = "Test wysłany"
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
            if not coordinator.last_update_success:
                raise RuntimeError("Nie udało się odświeżyć cen przed wysyłką")
            sent = await runtime_data.notifications.async_send_now_to_target(
                self._selected_target,
                options_override=self._ensure_working_options(),
                fuels_override=normalize_fuels(device.get(DEVICE_FUELS)),
                mode_override=normalize_notification_mode(
                    device.get(DEVICE_NOTIFICATION_MODE)
                ),
                device_override=device,
            )
            if not sent:
                raise RuntimeError("Nie udało się wysłać powiadomienia")
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Nie udało się wysłać bieżącego powiadomienia na %s",
                self._selected_target,
            )
            self._phone_status = "Błąd wysyłki"
        else:
            self._phone_status = "Powiadomienie wysłane"
        return await self.async_step_phone_menu()

    async def async_step_diagnostics(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show a compact diagnostics and actions menu."""
        runtime = self.config_entry.runtime_data
        coordinator = runtime.coordinator
        notifications = runtime.notifications
        data = coordinator.data
        tomorrow_status = "opublikowano" if data.tomorrow is not None else "oczekiwanie"
        last_error = coordinator.last_error_message or "brak"
        missing = notifications.missing_enabled_targets
        return self.async_show_menu(
            step_id="diagnostics",
            menu_options=["diagnostics_refresh", "diagnostics_send_all", "init"],
            description_placeholders={
                "tomorrow_status": tomorrow_status,
                "fetched_at": data.fetched_at.isoformat(),
                "parsed_periods": str(data.parsed_periods),
                "history_days": str(
                    max(
                        runtime.history.available_days(fuel, data.today_date)
                        for fuel in FUELS
                    )
                ),
                "last_error": last_error,
                "missing_targets": ", ".join(missing) if missing else "brak",
                "action_status": self._diagnostic_status or "-",
            },
        )

    async def async_step_diagnostics_refresh(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Force an immediate data refresh."""
        coordinator = self.config_entry.runtime_data.coordinator
        try:
            await coordinator.async_request_refresh()
            if not coordinator.last_update_success:
                raise RuntimeError("Nie udało się odświeżyć cen")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Ręczne sprawdzenie cen nie powiodło się")
            self._diagnostic_status = "Błąd sprawdzania danych"
        else:
            self._diagnostic_status = "Dane sprawdzone"
        return await self.async_step_diagnostics()

    async def async_step_diagnostics_send_all(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Send the current notification to all enabled phones."""
        runtime = self.config_entry.runtime_data
        try:
            await runtime.coordinator.async_request_refresh()
            if not runtime.coordinator.last_update_success:
                raise RuntimeError("Nie udało się odświeżyć cen przed wysyłką")
            count = await runtime.notifications.async_send_now_to_all(
                devices_override=list(self._existing_devices().values()),
                options_override=self._ensure_working_options(),
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Ręczna wysyłka do wszystkich telefonów nie powiodła się")
            self._diagnostic_status = "Błąd wysyłki"
        else:
            self._diagnostic_status = f"Wysłano do {count} telefonów"
        return await self.async_step_diagnostics()

    async def async_step_save(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Save all changes and reload the integration."""
        working = self._ensure_working_options()
        return self.async_create_entry(
            title="",
            data=merge_working_options(
                self._base_options or {},
                working,
                self.config_entry.options,
            ),
        )
