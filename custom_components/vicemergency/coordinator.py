"""Shared DataUpdateCoordinator for VicEmergency.

Single coordinator fetches the full feed once per cycle.
Each config entry (zone) registers itself and receives a filtered,
distance-sorted view of incidents within its radius.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_EXCLUDED_FEEDTYPES, DEFAULT_SCAN_INTERVAL, DOMAIN
from .feed.client import FeedFetchError, VicEmergencyFeedClient
from .feed.entry import VicEmergencyIncident
from .feed.manager import FeedDiff, FeedManager

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneConfig:
    """Configuration for a single monitoring zone."""

    entry_id: str
    name: str
    latitude: float
    longitude: float
    radius_km: float
    exclude_categories: list[str]
    include_statewide: bool
    scan_interval: int


class VicEmergencyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Shared coordinator: one fetch, many zones."""

    def __init__(self, hass: HomeAssistant, scan_interval: int) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._feed_client = VicEmergencyFeedClient(async_get_clientsession(hass))
        self._zones: dict[str, ZoneConfig] = {}
        self._feed_managers: dict[str, FeedManager] = {}
        self._all_incidents: list[VicEmergencyIncident] = []

    @property
    def feed_client(self) -> VicEmergencyFeedClient:
        return self._feed_client

    @property
    def all_incidents(self) -> list[VicEmergencyIncident]:
        return self._all_incidents

    @property
    def zones(self) -> dict[str, ZoneConfig]:
        return self._zones

    def add_zone(self, config: ZoneConfig) -> None:
        self._zones[config.entry_id] = config
        self._feed_managers[config.entry_id] = FeedManager()
        self._recalculate_interval()

    def remove_zone(self, entry_id: str) -> None:
        self._zones.pop(entry_id, None)
        manager = self._feed_managers.pop(entry_id, None)
        if manager:
            manager.reset()
        self._recalculate_interval()

    @property
    def is_empty(self) -> bool:
        return len(self._zones) == 0

    def get_zone_incidents(self, entry_id: str) -> list[VicEmergencyIncident]:
        zone = self._zones.get(entry_id)
        if zone is None or self.data is None:
            return []
        return self.data.get(entry_id, {}).get("incidents", [])

    def get_zone_diff(self, entry_id: str) -> FeedDiff | None:
        if self.data is None:
            return None
        return self.data.get(entry_id, {}).get("diff")

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            self._all_incidents = await self._feed_client.fetch()
        except FeedFetchError as err:
            raise UpdateFailed(str(err)) from err

        result: dict[str, Any] = {}
        for entry_id, zone in self._zones.items():
            filtered = self._filter_for_zone(self._all_incidents, zone)
            manager = self._feed_managers.get(entry_id)
            diff = manager.update(filtered) if manager else None

            if diff:
                self._fire_events(zone, diff)

            result[entry_id] = {"incidents": filtered, "diff": diff}

        return result

    def _filter_for_zone(
        self, incidents: list[VicEmergencyIncident], zone: ZoneConfig,
    ) -> list[VicEmergencyIncident]:
        filtered: list[VicEmergencyIncident] = []

        for incident in incidents:
            # Skip informational feedtypes (e.g. burn-area) that aren't active incidents
            if incident.feedtype in DEFAULT_EXCLUDED_FEEDTYPES:
                continue

            incident.compute_distance(zone.latitude, zone.longitude)

            if incident.statewide and zone.include_statewide:
                if incident.category_group not in zone.exclude_categories:
                    filtered.append(incident)
                continue

            if (
                incident.distance_km is not None
                and incident.distance_km <= zone.radius_km
                and incident.category_group not in zone.exclude_categories
            ):
                filtered.append(incident)

        filtered.sort(key=lambda i: i.distance_km or float("inf"))
        return filtered

    def _fire_events(self, zone: ZoneConfig, diff: FeedDiff) -> None:
        for incident in diff.new:
            self.hass.bus.async_fire(
                f"{DOMAIN}_incident_new",
                {"zone": zone.name, "entry_id": zone.entry_id, **incident.as_dict()},
            )
        for incident, changed_fields in diff.updated:
            self.hass.bus.async_fire(
                f"{DOMAIN}_incident_updated",
                {"zone": zone.name, "entry_id": zone.entry_id, "changed_fields": changed_fields, **incident.as_dict()},
            )
        for incident in diff.removed:
            self.hass.bus.async_fire(
                f"{DOMAIN}_incident_removed",
                {"zone": zone.name, "entry_id": zone.entry_id, "incident_id": incident.id,
                 "category1": incident.category1, "location": incident.location},
            )

    def _recalculate_interval(self) -> None:
        if not self._zones:
            return
        shortest = min(z.scan_interval for z in self._zones.values())
        self.update_interval = timedelta(seconds=shortest)
