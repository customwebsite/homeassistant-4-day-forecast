"""Constants for the VicEmergency integration."""

from __future__ import annotations

DOMAIN = "vicemergency"
MANUFACTURER = "Emergency Management Victoria"
ATTRIBUTION = (
    "Data provided by the State of Victoria, Australia under "
    "Creative Commons Attribution 3.0 Australia"
)

# ---------------------------------------------------------------------------
# Configuration keys
# ---------------------------------------------------------------------------

CONF_NAME = "name"
CONF_LOCATION = "location"
CONF_RADIUS = "radius"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_EXCLUDE_CATEGORIES = "exclude_categories"
CONF_INCLUDE_STATEWIDE = "include_statewide"

DEFAULT_NAME = "VicEmergency"
DEFAULT_RADIUS = 50.0  # km
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
MIN_SCAN_INTERVAL = 120  # 2 minutes
MAX_SCAN_INTERVAL = 86400  # 24 hours

# ---------------------------------------------------------------------------
# Feed endpoints
# ---------------------------------------------------------------------------

FEED_URL_PRIMARY = (
    "https://emergency.vic.gov.au/public/osom-geojson.json"
)
FEED_URL_FALLBACK_JSON = (
    "https://data.emergency.vic.gov.au/Show?pageId=getIncidentJSON"
)
FEED_URL_FALLBACK_XML = (
    "https://data.emergency.vic.gov.au/Show?pageId=getIncidentXML"
)

# ---------------------------------------------------------------------------
# Feed types to exclude by default (informational, not active incidents)
# ---------------------------------------------------------------------------

DEFAULT_EXCLUDED_FEEDTYPES: set[str] = {
    "burn-area",
}

# ---------------------------------------------------------------------------
# Fallback strategy constants
# ---------------------------------------------------------------------------

PRIMARY_FAIL_THRESHOLD = 3
PRIMARY_RETRY_INTERVAL = 10
STALENESS_WINDOW = 3600  # 60 minutes

# ---------------------------------------------------------------------------
# Category group mapping
# ---------------------------------------------------------------------------

CATEGORY_GROUPS: dict[str, str] = {
    "Fire": "fire",
    "Bushfire": "fire",
    "Planned Burn": "fire",
    "Burn Area": "fire",
    "Burn Advice": "fire",
    "Flood": "flood",
    "Riverine Flood": "flood",
    "Flash Flood": "flood",
    "Coastal Flood": "flood",
    "Dam Failure": "flood",
    "Storm": "storm_weather",
    "Severe Storm": "storm_weather",
    "Severe Weather": "storm_weather",
    "Severe Thunderstorm": "storm_weather",
    "Damaging Winds": "storm_weather",
    "Tornado/Cyclone": "storm_weather",
    "Earthquake": "storm_weather",
    "Tsunami": "storm_weather",
    "Landslide": "storm_weather",
    "Vehicle Accident": "transport",
    "Aircraft Accident": "transport",
    "Rail Accident": "transport",
    "Marine Accident": "transport",
    "Rescue": "transport",
    "Hazardous Material": "hazmat_health",
    "Medical": "hazmat_health",
    "Animal Health": "hazmat_health",
    "Dangerous Animal": "hazmat_health",
    "Oiled Wildlife": "hazmat_health",
    "Animal Plague": "hazmat_health",
    "Insect Plague": "hazmat_health",
    "Shark Sighting": "hazmat_health",
    "Water Pollution": "hazmat_health",
    "Plant Health": "hazmat_health",
    "Tree Down": "outages_closures",
    "Building Damage": "outages_closures",
    "Fallen Power Lines": "outages_closures",
    "Road Closed": "outages_closures",
    "Road Affected": "outages_closures",
    "Rail Disruption": "outages_closures",
    "Power Outage": "outages_closures",
    "Gas Outage": "outages_closures",
    "Water Outage": "outages_closures",
    "Park/Forest Closure": "outages_closures",
    "Beach Closure": "outages_closures",
    "School Closure": "outages_closures",
}

SUMMARY_GROUPS: list[str] = [
    "fire",
    "flood",
    "storm_weather",
    "transport",
    "hazmat_health",
    "outages_closures",
]

GROUP_FRIENDLY_NAMES: dict[str, str] = {
    "fire": "Fire",
    "flood": "Flood",
    "storm_weather": "Storm & Weather",
    "transport": "Transport",
    "hazmat_health": "Hazmat & Health",
    "outages_closures": "Outages & Closures",
}

# ---------------------------------------------------------------------------
# MDI icons
# ---------------------------------------------------------------------------

CATEGORY_ICONS: dict[str, str] = {
    "Fire": "mdi:fire",
    "Bushfire": "mdi:fire",
    "Planned Burn": "mdi:fire-alert",
    "Burn Area": "mdi:fire-alert",
    "Burn Advice": "mdi:fire-alert",
    "Flood": "mdi:flood",
    "Dam Failure": "mdi:flood",
    "Storm": "mdi:weather-lightning",
    "Damaging Winds": "mdi:weather-windy",
    "Tornado/Cyclone": "mdi:weather-tornado",
    "Earthquake": "mdi:earth",
    "Tsunami": "mdi:waves",
    "Landslide": "mdi:landslide",
    "Vehicle Accident": "mdi:car-emergency",
    "Aircraft Accident": "mdi:airplane-alert",
    "Rail Accident": "mdi:train-variant",
    "Marine Accident": "mdi:ferry",
    "Rescue": "mdi:ambulance",
    "Hazardous Material": "mdi:biohazard",
    "Medical": "mdi:hospital-box",
    "Animal Health": "mdi:paw",
    "Dangerous Animal": "mdi:alert-octagon",
    "Oiled Wildlife": "mdi:paw",
    "Animal Plague": "mdi:bug",
    "Insect Plague": "mdi:bug",
    "Shark Sighting": "mdi:shark-fin",
    "Water Pollution": "mdi:water-alert",
    "Plant Health": "mdi:sprout",
    "Tree Down": "mdi:tree",
    "Building Damage": "mdi:home-alert",
    "Fallen Power Lines": "mdi:transmission-tower-off",
    "Road Closed": "mdi:road-variant",
    "Road Affected": "mdi:road-variant",
    "Rail Disruption": "mdi:train-variant",
    "Power Outage": "mdi:flash-off",
    "Gas Outage": "mdi:gas-burner",
    "Water Outage": "mdi:water-off",
    "Park/Forest Closure": "mdi:pine-tree",
    "Beach Closure": "mdi:beach",
    "School Closure": "mdi:school",
}

DEFAULT_ICON = "mdi:alert"

GROUP_ICONS: dict[str, str] = {
    "fire": "mdi:fire",
    "flood": "mdi:flood",
    "storm_weather": "mdi:weather-lightning",
    "transport": "mdi:car-emergency",
    "hazmat_health": "mdi:biohazard",
    "outages_closures": "mdi:road-variant",
}

# ---------------------------------------------------------------------------
# Australian Warning System levels
# ---------------------------------------------------------------------------

WARNING_LEVELS: dict[str, int] = {
    "advice": 1,
    "watch_and_act": 2,
    "emergency_warning": 3,
}

FEEDTYPE_WARNING_MAP: dict[str, str] = {
    "warning": "advice",
    "watch-and-act": "watch_and_act",
    "emergency-warning": "emergency_warning",
}

WARNING_COLOURS: dict[str, str] = {
    "none": "#808080",
    "advice": "#FFCC00",
    "watch_and_act": "#FF6600",
    "emergency_warning": "#CC0000",
}
