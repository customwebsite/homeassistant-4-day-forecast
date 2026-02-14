"""CFA Fire Forecast integration for Home Assistant.

Fetches fire danger ratings and Total Fire Ban status from the
Country Fire Authority (CFA) Victoria RSS feeds.
"""

from __future__ import annotations

import logging
import os

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_DISTRICT, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import CfaFireForecastCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

_CARD_REGISTERED_KEY = f"{DOMAIN}_card_registered"
_COORDINATOR_KEY = "coordinator"
_ENTRIES_KEY = "entries"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the CFA Fire Forecast component (domain-level, runs once).

    Registers the custom Lovelace card as a static resource so users
    don't need to add it manually.
    """
    hass.data.setdefault(DOMAIN, {})

    # Serve the card JS from inside the component directory
    www_path = os.path.join(os.path.dirname(__file__), "www")
    if os.path.isdir(www_path):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    url_path=f"/{DOMAIN}_ui",
                    path=www_path,
                    cache_headers=True,
                )
            ]
        )
        _LOGGER.debug("Registered static path /%s_ui -> %s", DOMAIN, www_path)

        # Auto-register Lovelace resource (once only, after HA fully starts)
        if not hass.data[DOMAIN].get(_CARD_REGISTERED_KEY):

            async def _register_card(event=None) -> None:
                """Register the card JS as a Lovelace resource."""
                resource_url = f"/{DOMAIN}_ui/cfa-fire-forecast-card.js"

                if "lovelace" not in hass.data:
                    return

                ll_data = hass.data["lovelace"]
                resources = (
                    getattr(ll_data, "resources", None)
                    if hasattr(ll_data, "resources")
                    else ll_data.get("resources")
                )
                if not resources:
                    return

                # Check if already registered (any version)
                try:
                    for res in resources.async_items():
                        url = res.get("url", "")
                        if DOMAIN in url and "cfa-fire-forecast-card" in url:
                            hass.data[DOMAIN][_CARD_REGISTERED_KEY] = True
                            return
                except Exception:  # noqa: BLE001
                    return

                try:
                    await resources.async_create_item(
                        {"res_type": "module", "url": resource_url}
                    )
                    hass.data[DOMAIN][_CARD_REGISTERED_KEY] = True
                    _LOGGER.info("Auto-registered Lovelace card: %s", resource_url)
                except Exception:  # noqa: BLE001
                    _LOGGER.debug("Could not auto-register Lovelace card", exc_info=True)

            hass.bus.async_listen_once("homeassistant_started", _register_card)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CFA Fire Forecast from a config entry.

    Uses a shared coordinator so that all district entries share a single
    HTTP request to the combined CFA RSS feed.
    """
    hass.data.setdefault(DOMAIN, {})
    district_slug = entry.data[CONF_DISTRICT]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # Create or reuse the shared coordinator
    coordinator: CfaFireForecastCoordinator | None = hass.data[DOMAIN].get(
        _COORDINATOR_KEY
    )
    if coordinator is None:
        coordinator = CfaFireForecastCoordinator(hass, scan_interval)
        hass.data[DOMAIN][_COORDINATOR_KEY] = coordinator
    else:
        # Use the shortest scan interval across all entries
        current = coordinator.update_interval.total_seconds()
        if scan_interval < current:
            coordinator.update_interval_seconds(scan_interval)

    # Register this district with the shared coordinator
    coordinator.add_district(district_slug)

    # Perform initial data fetch (or reuse cached data)
    await coordinator.async_config_entry_first_refresh()

    # Store per-entry references
    hass.data[DOMAIN].setdefault(_ENTRIES_KEY, {})[entry.entry_id] = {
        "district_slug": district_slug,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the entry so changes take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_data = hass.data[DOMAIN].get(_ENTRIES_KEY, {}).pop(entry.entry_id, None)
        if entry_data:
            district_slug = entry_data["district_slug"]
            coordinator: CfaFireForecastCoordinator = entry_data["coordinator"]
            coordinator.remove_district(district_slug)

            # If no more districts tracked, remove the shared coordinator
            if not coordinator.tracked_districts:
                hass.data[DOMAIN].pop(_COORDINATOR_KEY, None)
                _LOGGER.debug("Removed shared coordinator (no districts tracked)")

    return unload_ok
