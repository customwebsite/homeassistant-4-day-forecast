# Future Enhancements & Feed Reference

This document catalogues the data available from CFA feeds, what this integration currently uses, and ideas for future development. It serves as a living reference for contributors.

The CFA Fire Danger Forecast integration is a **planning tool** — it helps users prepare for the days ahead by providing forecast fire danger ratings and Total Fire Ban status. Enhancement ideas should be evaluated against this planning purpose.

---

## 1. Current Entities (v1.1.0)

### Sensors (per district, up to 10)

| Entity suffix | Type | Description |
|---|---|---|
| `_fire_danger_rating_today` | `sensor` | Today's fire danger rating (NO RATING through CATASTROPHIC) |
| `_fire_danger_rating_tomorrow` | `sensor` | Tomorrow's fire danger rating |
| `_fire_danger_rating_day_3` | `sensor` | Day 3 fire danger rating |
| `_fire_danger_rating_day_4` | `sensor` | Day 4 fire danger rating |
| `_total_fire_ban_today` | `sensor` | Today's TFB status (Yes/No) |
| `_total_fire_ban_tomorrow` | `sensor` | Tomorrow's TFB status |
| `_total_fire_ban_day_3` | `sensor` | Day 3 TFB status |
| `_total_fire_ban_day_4` | `sensor` | Day 4 TFB status |
| `_max_fire_danger_rating` | `sensor` | Highest rating across all forecast days |
| `_feed_status` | `sensor` | Diagnostic: ok / degraded / failed |

Rating and TFB sensor count depends on the configured forecast days (1–4).

---

## 2. CFA RSS Feed Properties

### Combined Feed

**URL:** `https://www.cfa.vic.gov.au/cfa/rssfeed/tfbfdrforecast_rss.xml`

Returns data for all 9 fire districts in a single response. Each `<item>` contains:

| Field | Currently parsed | Notes |
|---|---|---|
| `<title>` | ✅ | District name and date |
| `<description>` | ✅ | Contains fire danger rating, TFB status |
| `<pubDate>` | ✅ | RSS publication timestamp |
| `<link>` | ❌ | CFA website link for the district |
| `<guid>` | ❌ | Unique identifier for the item |
| `<category>` | ❌ | May contain district or severity classification |

### Individual District Feeds

**URL pattern:** `https://www.cfa.vic.gov.au/cfa/rssfeed/{slug}-firedistrict_rss.xml`

Same structure as combined feed but filtered to a single district. Used as fallback when combined feed fails.

### Description Field Content (parsed)

The `<description>` field contains embedded data including:

| Data point | Currently extracted | Notes |
|---|---|---|
| Fire danger rating text | ✅ | e.g. "HIGH", "EXTREME" |
| Total Fire Ban status | ✅ | Yes/No/TBC |
| Forecast date | ✅ | Day label |
| Forecast issued timestamp | ✅ | BoM issue time |
| Statewide TFB declaration | ✅ | Boolean |

---

## 3. AFDRS Rating Values

| Rating | Severity | Hex Colour | Meaning |
|---|---|---|---|
| NO RATING | 0 | `#808080` | No forecast available |
| LOW-MODERATE | 1 | `#68A03A` | Plan and prepare |
| MODERATE | 2 | `#68A03A` | Be ready to act |
| HIGH | 3 | `#FED530` | Be ready to act |
| EXTREME | 4 | `#FE8100` | Take action now to protect life |
| CATASTROPHIC | 5 | `#E8352D` | For your survival, leave early |

---

## 4. Potential Future Sensors

### High Priority

| Sensor | Type | Description |
|---|---|---|
| **Binary TFB sensor** | `binary_sensor` | ON when Total Fire Ban is declared (simpler for automations than checking "Yes"/"No" text) |
| **Binary elevated danger** | `binary_sensor` | ON when rating is HIGH or above |
| **District trend** | `sensor` attr | Rating increasing/decreasing/stable across forecast days |
| **Grassland curing percentage** | `sensor` | Grassland fuel dryness — a key factor in fire behaviour planning |

### Medium Priority

| Sensor | Type | Description |
|---|---|---|
| **Cross-district max** | `sensor` | Highest rating across ALL configured districts |
| **Days until TFB** | `sensor` | Number of days until next Total Fire Ban (from forecast) |
| **Fire Danger Period active** | `binary_sensor` | Whether the Fire Danger Period is currently declared for the municipality |
| **Fire weather forecast** | `sensor` attr | Key weather factors driving the rating (temperature, wind, humidity) from BoM |

### Lower Priority

| Sensor | Type | Description |
|---|---|---|
| **Historical comparison** | `sensor` attr | How current rating compares to historical average for this date |
| **Season summary** | `sensor` attr | Count of Extreme/Catastrophic days this fire season |
| **Exemptions info** | `sensor` attr | TFB exemption categories and conditions |

---

## 5. Potential Future Features

### Card Enhancements

- **District map view**: Show Victoria map with colour-coded districts
- **Weekly calendar view**: Fire danger calendar showing the full week ahead
- **Rating trend arrows**: Up/down indicators for tomorrow vs today
- **Multi-district comparison table**: Side-by-side view of all monitored districts

### Integration Enhancements

- **Automation blueprints**: Pre-built automations for common planning scenarios (e.g. "remind me the evening before an Extreme day", "notify when TFB declared for later in the week")
- **Notification templates**: Pre-formatted notifications with rating details and CFA links
- **Historical data**: Track and graph ratings over time via HA statistics
- **Binary sensor platform**: Dedicated binary sensors for TFB and elevated danger (currently only sensor platform)

### Additional Data Sources

| Source | URL | Data available |
|---|---|---|
| BOM Fire Weather | `bom.gov.au/vic/forecasts/fire-weather.shtml` | Detailed fire weather forecasts |
| Grassland Curing | Various state agencies | Fuel moisture data |
| CFA District Maps | CFA GIS services | District boundary polygons |
| CFA Fire Danger Periods | `cfa.vic.gov.au` | Municipal Fire Danger Period dates |

---

## 6. Attribution Requirements

CFA data is published by the Country Fire Authority, a Victorian government agency. Data should be attributed to the State of Victoria under [Creative Commons Attribution 3.0 Australia](https://creativecommons.org/licenses/by/3.0/au/).

Per [EMV Emergency Data licence terms](https://www.emv.vic.gov.au/responsibilities/victorias-warning-system/emergency-data):

1. Source must be identified as "State of Victoria, Australia"
2. Must include a link to the EMV emergency data page
3. Must display the last date and time an update was received from the data feed

The integration satisfies these via the `feed_published` attribute and the `feed_status` sensor tracking.

---

## 7. Related Projects & References

| Resource | URL |
|---|---|
| CFA Total Fire Bans & Ratings | https://www.cfa.vic.gov.au/warnings-restrictions/total-fire-bans-and-ratings |
| CFA RSS Feeds | https://www.cfa.vic.gov.au/rss-feeds |
| Australian Fire Danger Rating System | https://www.afac.com.au/initiative/afdrs |
| EMV Emergency Data | https://www.emv.vic.gov.au/responsibilities/victorias-warning-system/emergency-data |
| BoM Fire Weather Services | http://www.bom.gov.au/weather-services/fire-weather-centre/index.shtml |
| CFA WordPress Plugin (original) | https://github.com/customwebsite/cfa-4-day-forecast |

---

## 8. CFA Fire Districts

| Slug | Display Name | Approximate Coverage |
|---|---|---|
| `central` | Central | Greater Melbourne surrounds, Yarra Ranges, Mornington Peninsula |
| `north-central` | North Central | Bendigo, Macedon Ranges, Hepburn |
| `south-west` | South West | Geelong, Surf Coast, Colac, Warrnambool |
| `northern-country` | Northern Country | Shepparton, Seymour, Benalla |
| `north-east` | North East | Wangaratta, Alpine, Wodonga |
| `mallee` | Mallee | Mildura, Swan Hill, Buloke |
| `wimmera` | Wimmera | Horsham, Ararat, Stawell |
| `east-gippsland` | East Gippsland | Bairnsdale, Orbost, Mallacoota |
| `west-and-south-gippsland` | West & South Gippsland | Warragul, Leongatha, Wonthaggi |

---

*Last updated: March 2026 — v1.1.0*
