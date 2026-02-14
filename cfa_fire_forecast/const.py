"""Constants for the CFA Fire Forecast integration."""

DOMAIN = "cfa_fire_forecast"
MANUFACTURER = "Country Fire Authority (CFA)"
ATTRIBUTION = "Data provided by the Country Fire Authority (CFA) Victoria, Australia"

CONF_DISTRICT = "district"
CONF_DISTRICTS = "districts"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FORECAST_DAYS = "forecast_days"

DEFAULT_SCAN_INTERVAL = 1800  # 30 minutes in seconds
DEFAULT_FORECAST_DAYS = 4

# Combined CFA RSS feed containing ALL districts in one response (1 HTTP call)
CFA_COMBINED_RSS_URL = (
    "https://www.cfa.vic.gov.au/cfa/rssfeed/tfbfdrforecast_rss.xml"
)

# Per-district CFA RSS feed URL template (kept as fallback)
CFA_RSS_URL = "https://www.cfa.vic.gov.au/cfa/rssfeed/{slug}-firedistrict_rss.xml"

# Available fire districts (slug -> display name)
DISTRICTS = {
    "north-central": "North Central",
    "south-west": "South West",
    "northern-country": "Northern Country",
    "north-east": "North East",
    "central": "Central",
    "mallee": "Mallee",
    "wimmera": "Wimmera",
    "east-gippsland": "East Gippsland",
    "west-and-south-gippsland": "West & South Gippsland",
}

# Canonical district names as they appear in the CFA feed text.
# Some differ from display names (e.g. "&" vs "and").
DISTRICT_FEED_NAMES = {
    "north-central": "North Central",
    "south-west": "South West",
    "northern-country": "Northern Country",
    "north-east": "North East",
    "central": "Central",
    "mallee": "Mallee",
    "wimmera": "Wimmera",
    "east-gippsland": "East Gippsland",
    "west-and-south-gippsland": "West and South Gippsland",
}

# Fire danger ratings in ascending order of severity
FIRE_DANGER_RATINGS = [
    "NO RATING",
    "LOW-MODERATE",
    "MODERATE",
    "HIGH",
    "EXTREME",
    "CATASTROPHIC",
]

# Rating severity level (for numeric sensor / icon selection)
RATING_SEVERITY = {
    "NO RATING": 0,
    "LOW-MODERATE": 1,
    "MODERATE": 2,
    "HIGH": 3,
    "EXTREME": 4,
    "CATASTROPHIC": 5,
}

# Colours matching official AFDRS (Australian Fire Danger Rating System)
# Moderate=green, High=yellow, Extreme=orange, Catastrophic=red
RATING_COLOURS = {
    "NO RATING": "#ACACAC",
    "LOW-MODERATE": "#8DC44D",
    "MODERATE": "#4EA346",
    "HIGH": "#F5C518",
    "EXTREME": "#E55B25",
    "CATASTROPHIC": "#CC2200",
}

# MDI icons per rating level for entity display
RATING_ICONS = {
    "NO RATING": "mdi:shield-check",
    "LOW-MODERATE": "mdi:fire",
    "MODERATE": "mdi:fire",
    "HIGH": "mdi:fire-alert",
    "EXTREME": "mdi:alert-octagon",
    "CATASTROPHIC": "mdi:skull-crossbones",
}
