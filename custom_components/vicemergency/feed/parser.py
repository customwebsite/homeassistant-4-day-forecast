"""Parsers for the VicEmergency feed formats.

Three endpoints, three parsers, one output type (VicEmergencyIncident).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

from .entry import VicEmergencyIncident

_LOGGER = logging.getLogger(__name__)


def parse_geojson(raw: dict[str, Any]) -> list[VicEmergencyIncident]:
    """Parse the primary GeoJSON FeatureCollection into incidents."""
    features = raw.get("features")
    if not isinstance(features, list):
        _LOGGER.warning("GeoJSON response missing 'features' list (type=%s)", raw.get("type"))
        return []

    incidents: list[VicEmergencyIncident] = []
    for feature in features:
        try:
            incident = _parse_geojson_feature(feature)
            if incident is not None:
                incidents.append(incident)
        except Exception:
            _LOGGER.debug(
                "Skipping malformed GeoJSON feature: %s",
                feature.get("properties", {}).get("id", "unknown"),
                exc_info=True,
            )
    return incidents


def _parse_geojson_feature(feature: dict[str, Any]) -> VicEmergencyIncident | None:
    """Parse one GeoJSON Feature into an incident."""
    props = feature.get("properties", {})
    geometry = feature.get("geometry", {})

    lat, lon = _extract_coordinates(geometry)
    if lat is None or lon is None:
        return None

    incident_id = props.get("id")
    if not incident_id:
        return None

    return VicEmergencyIncident(
        id=str(incident_id),
        source_title=props.get("sourceTitle", ""),
        category1=props.get("category1", ""),
        category2=props.get("category2", ""),
        feedtype=props.get("feedType", "incident"),
        status=props.get("status", ""),
        source_org=props.get("sourceOrg", ""),
        location=props.get("location", ""),
        latitude=lat,
        longitude=lon,
        description=props.get("description", ""),
        size=props.get("size"),
        size_formatted=props.get("sizeFormatted"),
        resources=_str_or_none(props.get("resources")),
        statewide=_parse_bool(props.get("statewide")),
        updated=_parse_datetime(props.get("updated")),
        esta_id=_str_or_none(props.get("id2")),
    )


def _extract_coordinates(geometry: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract lat/lon from a GeoJSON geometry."""
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates")
    if not coords:
        return None, None

    if geom_type == "Point":
        return float(coords[1]), float(coords[0])

    if geom_type == "Polygon":
        return _centroid(coords[0])

    if geom_type == "MultiPolygon":
        return _centroid(coords[0][0])

    return None, None


def _centroid(ring: list[list[float]]) -> tuple[float, float]:
    """Compute naive centroid of a coordinate ring."""
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return sum(lats) / len(lats), sum(lons) / len(lons)


# ---------------------------------------------------------------------------
# JSON fallback parser
# ---------------------------------------------------------------------------


def parse_json_fallback(raw: dict[str, Any]) -> list[VicEmergencyIncident]:
    """Parse the legacy JSON API response."""
    results = raw.get("results") or raw.get("incidents") or []
    if isinstance(raw, list):
        results = raw

    incidents: list[VicEmergencyIncident] = []
    for item in results:
        try:
            incident = _parse_json_item(item)
            if incident is not None:
                incidents.append(incident)
        except Exception:
            _LOGGER.debug(
                "Skipping malformed JSON fallback item: %s",
                item.get("id", "unknown"),
                exc_info=True,
            )
    return incidents


def _parse_json_item(item: dict[str, Any]) -> VicEmergencyIncident | None:
    """Parse a single item from the JSON fallback."""
    incident_id = item.get("id")
    if not incident_id:
        return None

    lat = _safe_float(item.get("lat"))
    lon = _safe_float(item.get("lon") or item.get("long"))
    if lat is None or lon is None:
        return None

    return VicEmergencyIncident(
        id=str(incident_id),
        source_title=item.get("sourceTitle", ""),
        category1=item.get("category1", ""),
        category2=item.get("category2", ""),
        feedtype=item.get("feedType", "incident"),
        status=item.get("status", ""),
        source_org=item.get("sourceOrg", ""),
        location=item.get("location", ""),
        latitude=lat,
        longitude=lon,
        description=item.get("description", ""),
        size=item.get("size"),
        size_formatted=item.get("sizeFormatted"),
        resources=_str_or_none(item.get("resources")),
        statewide=_parse_bool(item.get("statewide")),
        updated=_parse_datetime(item.get("updated")),
        esta_id=_str_or_none(item.get("id2")),
    )


# ---------------------------------------------------------------------------
# XML fallback parser
# ---------------------------------------------------------------------------


def parse_xml_fallback(xml_text: str) -> list[VicEmergencyIncident]:
    """Parse the XML fallback endpoint."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        _LOGGER.warning("Failed to parse XML fallback response")
        return []

    incidents: list[VicEmergencyIncident] = []
    for elem in root.iter("incident"):
        try:
            incident = _parse_xml_element(elem)
            if incident is not None:
                incidents.append(incident)
        except Exception:
            _LOGGER.debug("Skipping malformed XML incident element", exc_info=True)
    return incidents


def _parse_xml_element(elem: ElementTree.Element) -> VicEmergencyIncident | None:
    """Parse a single <incident> XML element."""
    incident_id = _xml_text(elem, "id")
    if not incident_id:
        return None

    lat = _safe_float(_xml_text(elem, "lat"))
    lon = _safe_float(_xml_text(elem, "lon") or _xml_text(elem, "long"))
    if lat is None or lon is None:
        return None

    return VicEmergencyIncident(
        id=incident_id,
        source_title=_xml_text(elem, "sourceTitle") or "",
        category1=_xml_text(elem, "category1") or "",
        category2=_xml_text(elem, "category2") or "",
        feedtype=_xml_text(elem, "feedType") or "incident",
        status=_xml_text(elem, "status") or "",
        source_org=_xml_text(elem, "sourceOrg") or "",
        location=_xml_text(elem, "location") or "",
        latitude=lat,
        longitude=lon,
        description=_xml_text(elem, "description") or "",
        size=_xml_text(elem, "size"),
        size_formatted=_xml_text(elem, "sizeFormatted"),
        resources=_xml_text(elem, "resources"),
        statewide=_parse_bool(_xml_text(elem, "statewide")),
        updated=_parse_datetime(_xml_text(elem, "updated")),
        esta_id=_xml_text(elem, "id2"),
    )


def _xml_text(parent: ElementTree.Element, tag: str) -> str | None:
    """Safely extract text content from an XML child element."""
    child = parent.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse a datetime string, returning None on failure."""
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_bool(value: Any) -> bool:
    """Parse a boolean value from various feed representations."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return bool(value) if value is not None else False


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        result = float(value)
        if result == 0.0:
            return None
        return result
    except (ValueError, TypeError):
        return None


def _str_or_none(value: Any) -> str | None:
    """Return a non-empty string or None."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None
