"""Sensor platform for the VicEmergency integration.

Creates per zone: total count, per-group counts, highest warning,
nearest incident, and feed status diagnostic.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION, DOMAIN, GROUP_FRIENDLY_NAMES, GROUP_ICONS,
    MANUFACTURER, SUMMARY_GROUPS, WARNING_COLOURS, WARNING_LEVELS,
)
from .coordinator import VicEmergencyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up VicEmergency sensors from a config entry."""
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    coordinator: VicEmergencyCoordinator = entry_data["coordinator"]
    zone_name: str = entry_data["zone_config"].name

    entities: list[SensorEntity] = [
        VicEmergencyTotalCountSensor(coordinator, entry, zone_name),
        *(VicEmergencyGroupCountSensor(coordinator, entry, zone_name, group) for group in SUMMARY_GROUPS),
        VicEmergencyHighestWarningSensor(coordinator, entry, zone_name),
        VicEmergencyNearestSensor(coordinator, entry, zone_name),
        VicEmergencyFeedStatusSensor(coordinator, entry, zone_name),
    ]

    async_add_entities(entities, update_before_add=True)


class VicEmergencyBaseSensor(CoordinatorEntity[VicEmergencyCoordinator], SensorEntity):
    """Base class for all VicEmergency sensors."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: VicEmergencyCoordinator, entry: ConfigEntry, zone_name: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._zone_name = zone_name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"VicEmergency {self._zone_name}",
            manufacturer=MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://emergency.vic.gov.au",
        )

    def _get_incidents(self) -> list:
        return self.coordinator.get_zone_incidents(self._entry.entry_id)


class VicEmergencyTotalCountSensor(VicEmergencyBaseSensor):
    """Total number of active incidents in the zone."""

    def __init__(self, coordinator, entry, zone_name):
        super().__init__(coordinator, entry, zone_name)
        self._attr_unique_id = f"{entry.entry_id}_total_incidents"
        self._attr_name = "Total Incidents"
        self._attr_icon = "mdi:alert-circle"
        self._attr_native_unit_of_measurement = "incidents"
        self._attr_state_class = "measurement"

    @property
    def native_value(self) -> int:
        return len(self._get_incidents())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        incidents = self._get_incidents()
        counts: dict[str, int] = {}
        for group in SUMMARY_GROUPS:
            counts[group] = sum(1 for i in incidents if i.category_group == group)
        other = sum(1 for i in incidents if i.category_group == "other")
        if other:
            counts["other"] = other
        return counts


class VicEmergencyGroupCountSensor(VicEmergencyBaseSensor):
    """Count of incidents for a specific category group."""

    def __init__(self, coordinator, entry, zone_name, group):
        super().__init__(coordinator, entry, zone_name)
        self._group = group
        friendly = GROUP_FRIENDLY_NAMES.get(group, group)
        self._attr_unique_id = f"{entry.entry_id}_{group}_count"
        self._attr_name = f"{friendly} Incidents"
        self._attr_icon = GROUP_ICONS.get(group, "mdi:alert")
        self._attr_native_unit_of_measurement = "incidents"
        self._attr_state_class = "measurement"

    @property
    def native_value(self) -> int:
        return sum(1 for i in self._get_incidents() if i.category_group == self._group)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        matching = [i for i in self._get_incidents() if i.category_group == self._group]
        if not matching:
            return {}
        return {
            "incidents": [
                {
                    "id": i.id, "title": i.source_title, "category": i.category1,
                    "status": i.status, "location": i.location,
                    "distance_km": round(i.distance_km, 1) if i.distance_km else None,
                }
                for i in matching[:10]
            ]
        }


class VicEmergencyHighestWarningSensor(VicEmergencyBaseSensor):
    """Highest Australian Warning System level across all incidents in zone."""

    def __init__(self, coordinator, entry, zone_name):
        super().__init__(coordinator, entry, zone_name)
        self._attr_unique_id = f"{entry.entry_id}_highest_warning"
        self._attr_name = "Highest Warning Level"

    @property
    def native_value(self) -> str:
        max_level = 0
        max_name = "none"
        for incident in self._get_incidents():
            wl = incident.warning_level
            if wl and WARNING_LEVELS.get(wl, 0) > max_level:
                max_level = WARNING_LEVELS[wl]
                max_name = wl
        return max_name

    @property
    def icon(self) -> str:
        level = self.native_value
        if level == "emergency_warning":
            return "mdi:alert-octagon"
        if level == "watch_and_act":
            return "mdi:alert"
        if level == "advice":
            return "mdi:information"
        return "mdi:check-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        level = self.native_value
        warned = [i for i in self._get_incidents() if i.warning_level is not None]
        return {
            "colour": WARNING_COLOURS.get(level, WARNING_COLOURS["none"]),
            "warnings_count": len(warned),
        }


class VicEmergencyNearestSensor(VicEmergencyBaseSensor):
    """Distance to the nearest incident in the zone."""

    def __init__(self, coordinator, entry, zone_name):
        super().__init__(coordinator, entry, zone_name)
        self._attr_unique_id = f"{entry.entry_id}_nearest_incident"
        self._attr_name = "Nearest Incident"
        self._attr_icon = "mdi:map-marker-distance"
        self._attr_native_unit_of_measurement = "km"

    @property
    def native_value(self) -> float | None:
        incidents = self._get_incidents()
        if not incidents:
            return None
        nearest = incidents[0]
        if nearest.distance_km is not None:
            return round(nearest.distance_km, 1)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        incidents = self._get_incidents()
        if not incidents:
            return {}
        nearest = incidents[0]
        return {
            "incident_id": nearest.id,
            "title": nearest.source_title,
            "category": nearest.category1,
            "status": nearest.status,
            "location": nearest.location,
            "bearing": nearest.bearing,
            "feedtype": nearest.feedtype,
        }


class VicEmergencyFeedStatusSensor(VicEmergencyBaseSensor):
    """Diagnostic sensor showing feed health (ok / degraded / failed)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, zone_name):
        super().__init__(coordinator, entry, zone_name)
        self._attr_unique_id = f"{entry.entry_id}_feed_status"
        self._attr_name = "Feed Status"

    @property
    def native_value(self) -> str:
        client = self.coordinator.feed_client
        if self.coordinator.last_update_success is False:
            return "failed"
        if client.fallback_active:
            return "degraded"
        return "ok"

    @property
    def icon(self) -> str:
        state = self.native_value
        if state == "ok":
            return "mdi:rss"
        if state == "degraded":
            return "mdi:alert-circle-outline"
        return "mdi:alert-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        client = self.coordinator.feed_client
        attrs: dict[str, Any] = {
            "active_endpoint": client.active_endpoint,
            "primary_fail_count": client.primary_fail_count,
            "fallback_active": client.fallback_active,
        }
        if client.last_error:
            attrs["last_error"] = client.last_error
        return attrs
