"""Dataclass representing a single VicEmergency incident or warning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import atan2, cos, degrees, radians, sin, sqrt
from typing import Any

from ..const import CATEGORY_GROUPS


@dataclass
class VicEmergencyIncident:
    """Represents a single incident or warning from the VicEmergency feed."""

    # --- Identifiers ---
    id: str
    source_title: str

    # --- Classification ---
    category1: str
    category2: str
    feedtype: str
    status: str
    source_org: str

    # --- Location ---
    location: str
    latitude: float
    longitude: float

    # --- Content ---
    description: str = ""
    size: str | None = None
    size_formatted: str | None = None
    resources: str | None = None
    statewide: bool = False
    updated: datetime | None = None
    esta_id: str | None = None

    # --- Computed fields (set per-zone after parsing) ---
    distance_km: float | None = field(default=None, repr=False)
    bearing: str | None = field(default=None, repr=False)

    @property
    def category_group(self) -> str:
        """Map category1 to a summary group key."""
        return CATEGORY_GROUPS.get(self.category1, "other")

    @property
    def warning_level(self) -> str | None:
        """Derive the Australian Warning System level from feedtype."""
        from ..const import FEEDTYPE_WARNING_MAP
        return FEEDTYPE_WARNING_MAP.get(self.feedtype)

    def compute_distance(self, home_lat: float, home_lon: float) -> None:
        """Compute great-circle distance and bearing from a reference point."""
        self.distance_km = _haversine(home_lat, home_lon, self.latitude, self.longitude)
        self.bearing = _compass_bearing(home_lat, home_lon, self.latitude, self.longitude)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary of all fields."""
        return {
            "id": self.id,
            "source_title": self.source_title,
            "category1": self.category1,
            "category2": self.category2,
            "category_group": self.category_group,
            "feedtype": self.feedtype,
            "status": self.status,
            "source_org": self.source_org,
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "description": self.description,
            "size": self.size,
            "size_formatted": self.size_formatted,
            "resources": self.resources,
            "statewide": self.statewide,
            "updated": self.updated.isoformat() if self.updated else None,
            "esta_id": self.esta_id,
            "distance_km": round(self.distance_km, 2) if self.distance_km is not None else None,
            "bearing": self.bearing,
            "warning_level": self.warning_level,
        }


_EARTH_RADIUS_KM = 6371.0

_COMPASS_POINTS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    rlat1, rlon1, rlat2, rlon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    return _EARTH_RADIUS_KM * 2 * atan2(sqrt(a), sqrt(1 - a))


def _compass_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """Return 16-point compass bearing from point 1 to point 2."""
    rlat1, rlon1, rlat2, rlon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlon = rlon2 - rlon1
    x = sin(dlon) * cos(rlat2)
    y = cos(rlat1) * sin(rlat2) - sin(rlat1) * cos(rlat2) * cos(dlon)
    bearing_deg = (degrees(atan2(x, y)) + 360) % 360
    idx = int((bearing_deg + 11.25) / 22.5) % 16
    return _COMPASS_POINTS[idx]
