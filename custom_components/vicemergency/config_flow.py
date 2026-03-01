"""Config flow for the VicEmergency integration.

Config flow (immutable): name, location (map picker with radius).
Options flow (mutable): scan_interval, exclude_categories, include_statewide.
"""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    LocationSelector,
    LocationSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_EXCLUDE_CATEGORIES,
    CONF_INCLUDE_STATEWIDE,
    CONF_LOCATION,
    CONF_NAME,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FEED_URL_PRIMARY,
    GROUP_FRIENDLY_NAMES,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SUMMARY_GROUPS,
)


class VicEmergencyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow for VicEmergency."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._name: str = DEFAULT_NAME

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Zone name."""
        if user_input is not None:
            self._name = user_input.get(CONF_NAME, DEFAULT_NAME)
            return await self.async_step_location()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Map picker with radius."""
        errors: dict[str, str] = {}

        if user_input is not None:
            location = user_input.get(CONF_LOCATION, {})

            latitude = location.get("latitude")
            longitude = location.get("longitude")
            radius_m = location.get("radius", DEFAULT_RADIUS * 1000)

            if latitude is None or longitude is None:
                errors["base"] = "no_location"
            else:
                # Test connectivity to the primary feed
                session = async_get_clientsession(self.hass)
                try:
                    async with session.get(
                        FEED_URL_PRIMARY,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status != 200:
                            errors["base"] = "cannot_connect"
                except Exception:
                    errors["base"] = "cannot_connect"

            if not errors:
                await self.async_set_unique_id(
                    f"vicemergency_{latitude:.4f}_{longitude:.4f}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_NAME: self._name,
                        "latitude": latitude,
                        "longitude": longitude,
                        CONF_RADIUS: radius_m / 1000,
                    },
                )

        default_location = {
            "latitude": self.hass.config.latitude,
            "longitude": self.hass.config.longitude,
            "radius": DEFAULT_RADIUS * 1000,
        }

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATION, default=default_location
                    ): LocationSelector(
                        LocationSelectorConfig(radius=True, icon="mdi:alert")
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> VicEmergencyOptionsFlow:
        return VicEmergencyOptionsFlow()


class VicEmergencyOptionsFlow(config_entries.OptionsFlow):
    """Handle mutable options for VicEmergency."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        current_excludes = self.config_entry.options.get(CONF_EXCLUDE_CATEGORIES, [])
        current_statewide = self.config_entry.options.get(CONF_INCLUDE_STATEWIDE, True)

        category_options = [
            {"value": key, "label": GROUP_FRIENDLY_NAMES[key]}
            for key in SUMMARY_GROUPS
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL,
                            step=60, unit_of_measurement="seconds",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_EXCLUDE_CATEGORIES, default=current_excludes): SelectSelector(
                        SelectSelectorConfig(
                            options=category_options, multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                    vol.Optional(CONF_INCLUDE_STATEWIDE, default=current_statewide): bool,
                }
            ),
        )
