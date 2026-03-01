"""Diagnostics support for VicEmergency."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import VicEmergencyCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    entry_data = hass.data[DOMAIN]["entries"].get(entry.entry_id, {})
    coordinator: VicEmergencyCoordinator | None = entry_data.get("coordinator")

    diag: dict[str, Any] = {
        "config": dict(entry.data),
        "options": dict(entry.options),
    }

    if coordinator is not None:
        client = coordinator.feed_client
        incidents = coordinator.get_zone_incidents(entry.entry_id)
        diag["coordinator"] = {
            "active_endpoint": client.active_endpoint,
            "primary_fail_count": client.primary_fail_count,
            "fallback_active": client.fallback_active,
            "last_error": client.last_error,
            "total_zones": len(coordinator.zones),
            "all_incidents_count": len(coordinator.all_incidents),
            "zone_incidents_count": len(incidents),
            "last_update_success": coordinator.last_update_success,
        }

    return diag
