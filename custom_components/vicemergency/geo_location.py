"""Geo-location platform for the VicEmergency integration.

Creates a GeolocationEvent entity for each active incident in a zone.
These appear on the Home Assistant map and are dynamically created/removed.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CATEGORY_ICONS, DEFAULT_ICON, DOMAIN
from .coordinator import VicEmergencyCoordinator
from .feed.entry import VicEmergencyIncident

_LOGGER = logging.getLogger(__name__)
SOURCE = "vicemergency"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    coordinator: VicEmergencyCoordinator = entry_data["coordinator"]
    manager = GeoLocationManager(coordinator, entry, async_add_entities)
    manager.start()


class GeoLocationManager:
    """Manage the lifecycle of geo-location entities for one zone."""

    def __init__(self, coordinator, entry, async_add_entities):
        self._coordinator = coordinator
        self._entry = entry
        self._async_add_entities = async_add_entities
        self._tracked: dict[str, VicEmergencyGeoLocation] = {}

    def start(self) -> None:
        self._process_update()
        self._coordinator.async_add_listener(self._on_coordinator_update)

    @callback
    def _on_coordinator_update(self) -> None:
        self._process_update()

    def _process_update(self) -> None:
        incidents = self._coordinator.get_zone_incidents(self._entry.entry_id)
        current_ids = {i.id for i in incidents}
        incident_map = {i.id: i for i in incidents}

        # Remove entities for ended incidents
        for incident_id in set(self._tracked.keys()) - current_ids:
            entity = self._tracked.pop(incident_id, None)
            if entity is not None:
                entity.async_remove_self()

        # Update existing entities
        for incident_id in set(self._tracked.keys()) & current_ids:
            self._tracked[incident_id].update_incident(incident_map[incident_id])

        # Create entities for new incidents
        new_entities: list[VicEmergencyGeoLocation] = []
        for incident_id in current_ids - set(self._tracked.keys()):
            entity = VicEmergencyGeoLocation(
                self._coordinator, self._entry, incident_map[incident_id],
            )
            self._tracked[incident_id] = entity
            new_entities.append(entity)

        if new_entities:
            self._async_add_entities(new_entities)


class VicEmergencyGeoLocation(CoordinatorEntity[VicEmergencyCoordinator], GeolocationEvent):
    """A geo-location entity representing one active incident."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator, entry, incident: VicEmergencyIncident):
        super().__init__(coordinator)
        self._entry = entry
        self._incident = incident
        self._attr_unique_id = f"{entry.entry_id}_geo_{incident.id}"
        self._removed = False

    def update_incident(self, incident: VicEmergencyIncident) -> None:
        self._incident = incident
        self.async_write_ha_state()

    def async_remove_self(self) -> None:
        self._removed = True
        self.hass.async_create_task(self.async_remove())

    @property
    def available(self) -> bool:
        return not self._removed and super().available

    @property
    def name(self) -> str:
        return self._incident.source_title or self._incident.location or "Unknown"

    @property
    def source(self) -> str:
        return SOURCE

    @property
    def latitude(self) -> float | None:
        return self._incident.latitude

    @property
    def longitude(self) -> float | None:
        return self._incident.longitude

    @property
    def distance(self) -> float | None:
        return self._incident.distance_km

    @property
    def icon(self) -> str:
        return CATEGORY_ICONS.get(self._incident.category1, DEFAULT_ICON)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        i = self._incident
        attrs: dict[str, Any] = {
            "incident_id": i.id, "category1": i.category1, "category2": i.category2,
            "category_group": i.category_group, "feedtype": i.feedtype,
            "status": i.status, "source_org": i.source_org,
            "location": i.location, "bearing": i.bearing,
        }
        if i.size_formatted:
            attrs["size"] = i.size_formatted
        if i.resources:
            attrs["resources"] = i.resources
        if i.updated:
            attrs["updated"] = i.updated.isoformat()
        if i.warning_level:
            attrs["warning_level"] = i.warning_level
        return attrs
