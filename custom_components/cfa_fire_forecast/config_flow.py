"""Config flow for CFA Fire Forecast integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CFA_COMBINED_RSS_URL,
    CONF_DISTRICT,
    CONF_FORECAST_DAYS,
    CONF_SCAN_INTERVAL,
    DEFAULT_FORECAST_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DISTRICTS,
    DOMAIN,
)


class CfaFireForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CFA Fire Forecast."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step — choose a fire district."""
        errors: dict[str, str] = {}

        if user_input is not None:
            district = user_input[CONF_DISTRICT]

            # Prevent duplicate entries for the same district
            await self.async_set_unique_id(f"cfa_{district}")
            self._abort_if_unique_id_configured()

            # Validate connectivity using the combined feed
            session = async_get_clientsession(self.hass)
            try:
                async with session.get(CFA_COMBINED_RSS_URL, timeout=10) as resp:
                    if resp.status != 200:
                        errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"CFA – {DISTRICTS[district]}",
                    data={CONF_DISTRICT: district},
                )

        district_options = {slug: name for slug, name in DISTRICTS.items()}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DISTRICT, default="central"): vol.In(
                        district_options
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CfaFireForecastOptionsFlow:
        """Return the options flow handler."""
        return CfaFireForecastOptionsFlow()


class CfaFireForecastOptionsFlow(config_entries.OptionsFlow):
    """Handle options for CFA Fire Forecast."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_days = self.config_entry.options.get(
            CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=300, max=86400)),
                    vol.Optional(
                        CONF_FORECAST_DAYS,
                        default=current_days,
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=4)),
                }
            ),
        )
