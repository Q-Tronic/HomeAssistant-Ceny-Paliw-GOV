"""Config flow for Ceny paliw GOV.PL."""

from __future__ import annotations

from typing import Any

import probatio

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import DOMAIN, NAME


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
