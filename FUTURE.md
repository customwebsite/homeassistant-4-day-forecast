# Future Enhancements & Feed Reference

This document catalogues the data available from the VicEmergency feed, what this integration currently uses, and ideas for future development. It serves as a living reference for contributors.

---

## 1. Current Entities (v1.2.0)

### Sensors

| Entity suffix | Type | Description |
|---|---|---|
| `_total_incidents` | `sensor` | Count of active incidents in zone, with per-group breakdown in attributes |
| `_fire_incidents` | `sensor` | Count of fire-group incidents, with incident list in attributes |
| `_flood_incidents` | `sensor` | Count of flood-group incidents |
| `_storm_weather_incidents` | `sensor` | Count of storm/weather-group incidents |
| `_transport_incidents` | `sensor` | Count of transport-group incidents |
| `_hazmat_health_incidents` | `sensor` | Count of hazmat/health-group incidents |
| `_outages_closures_incidents` | `sensor` | Count of outages/closures-group incidents |
| `_highest_warning_level` | `sensor` | Highest Australian Warning System level (none / advice / watch_and_act / emergency_warning) |
| `_nearest_incident` | `sensor` | Distance (km) to nearest incident, with title, category, status, bearing in attributes |
| `_feed_status` | `sensor` | Diagnostic: ok / degraded / failed |

### Binary Sensors

| Entity suffix | Type | Description |
|---|---|---|
| `_fire_active` | `binary_sensor` | ON when ≥1 fire incident in zone |
| `_flood_active` | `binary_sensor` | ON when ≥1 flood incident in zone |
| `_storm_weather_active` | `binary_sensor` | ON when ≥1 storm/weather incident in zone |
| `_transport_active` | `binary_sensor` | ON when ≥1 transport incident in zone |
| `_hazmat_health_active` | `binary_sensor` | ON when ≥1 hazmat/health incident in zone |
| `_outages_closures_active` | `binary_sensor` | ON when ≥1 outage/closure incident in zone |

### Geo Location

| Entity | Description |
|---|---|
| `geo_location.vicemergency_*` | One entity per incident, shown on HA map card |

### Events

| Event | Description |
|---|---|
| `vicemergency_incident_new` | Fired when a new incident appears in a zone |
| `vicemergency_incident_update` | Fired when an existing incident is updated |
| `vicemergency_incident_remove` | Fired when an incident leaves a zone |

---

## 2. GeoJSON Feed Properties

The primary feed (`emergency.vic.gov.au/public/osom-geojson.json`) returns a GeoJSON FeatureCollection. Each Feature has `geometry` and `properties`.

### Properties Currently Parsed

| Property | Field in code | Used in sensors | Notes |
|---|---|---|---|
| `id` | `id` | ✅ All | Primary identifier |
| `id2` | `esta_id` | Nearest (attr) | ESTA CAD number |
| `sourceTitle` | `source_title` | ✅ All | Incident name (e.g. "Dalrymple Rd") |
| `category1` | `category1` | ✅ All | Primary category (e.g. "Fire", "Riverine Flood") |
| `category2` | `category2` | ❌ Stored only | Secondary category (rarely populated) |
| `feedType` | `feedtype` | ✅ Warning level | Determines warning level mapping |
| `status` | `status` | ✅ Nearest (attr) | e.g. "Going", "Controlled", "Under Control", "Unknown" |
| `sourceOrg` | `source_org` | ❌ Stored only | Reporting agency (e.g. "CFA", "VICSES", "BOM") |
| `location` | `location` | ✅ Nearest (attr) | Human-readable location |
| `description` | `description` | ❌ Stored only | Free-text description |
| `size` | `size` | ❌ Stored only | Numeric size (hectares for fires) |
| `sizeFormatted` | `size_formatted` | ❌ Stored only | e.g. "150 ha" |
| `resources` | `resources` | ❌ Stored only | Number of responding resources |
| `statewide` | `statewide` | ❌ Filter only | Whether this is a statewide alert |
| `updated` | `updated` | ❌ Stored only | Last update timestamp |
| `geometry` | `latitude/longitude` | ✅ All | Point, Polygon, or MultiPolygon |

### Properties Available but NOT Currently Parsed

These fields appear in the GeoJSON feed but are not extracted by the parser. They represent opportunities for future sensors.

| Property | Description | Potential use |
|---|---|---|
| `created` | Incident creation timestamp | Duration sensor, "time since reported" |
| `originId` | Original system incident ID | Cross-reference with agency systems |
| `webBody` | Full HTML description | Rich notification content |
| `webHeadline` | Short headline | Notification title |
| `municipalityCode` | LGA code | Filter by municipality |
| `municipality` | LGA name (e.g. "MACEDON RANGES") | Display in attributes, filter |
| `districtCode` | CFA district code | Filter by CFA district |
| `district` | CFA district name | Display in attributes |
| `regionCode` | EMV region code | Filter by region |
| `region` | EMV region name | Display in attributes |
| `cFARegion` | CFA region name | Display in attributes |
| `fireDistrict` | Fire weather district | Fire danger correlation |
| `sizeHa` | Area in hectares (numeric) | Fire size tracking sensor |
| `sizeFmt` | Formatted area string | Display |
| `resourceCount` | Number of resources deployed | Resource tracking sensor |
| `otherInfo` | Additional info string | Display in attributes |
| `cap_*` | CAP-AU fields (Common Alerting Protocol) | Standards-compliant alerting |
| `photoUrl` | Incident photo URL | Card enhancement |

---

## 3. Known Feed Values

### category1 Values (observed)

**Fire group:**
Fire, Bushfire, Planned Burn, Burn Area, Burn Advice

**Flood group:**
Flood, Riverine Flood, Flash Flood, Coastal Flood, Dam Failure

**Storm & Weather group:**
Storm, Severe Storm, Severe Weather, Severe Thunderstorm, Damaging Winds, Tornado/Cyclone, Earthquake, Tsunami, Landslide

**Transport group:**
Vehicle Accident, Aircraft Accident, Rail Accident, Marine Accident, Rescue

**Hazmat & Health group:**
Hazardous Material, Medical, Animal Health, Dangerous Animal, Oiled Wildlife, Animal Plague, Insect Plague, Shark Sighting, Water Pollution, Plant Health

**Outages & Closures group:**
Tree Down, Building Damage, Fallen Power Lines, Road Closed, Road Affected, Rail Disruption, Power Outage, Gas Outage, Water Outage, Park/Forest Closure, Beach Closure, School Closure

> **Note:** This list is based on observed values. EMV may add new categories at any time. Unmapped categories default to the "other" group and are included in the total count but not displayed in any specific chip.

### feedType Values (observed)

| feedType | Warning level mapping | Description |
|---|---|---|
| `incident` | none | Standard incident |
| `burn-area` | none | Historical/planned burn boundary (**filtered out by default**) |
| `warning` | Advice (yellow) | Advisory warning |
| `watch-and-act` | Watch & Act (orange) | Elevated threat |
| `emergency-warning` | Emergency Warning (red) | Immediate danger to life |

### status Values (observed)

| Status | Typical meaning |
|---|---|
| `Going` | Active and spreading (fire) |
| `Controlled` | Contained but not yet safe |
| `Under Control` | No longer spreading |
| `Safe` | Incident resolved |
| `Planned` | Scheduled activity (e.g. planned burn) |
| `Unknown` | Status not determined |
| `Completed` | Activity finished |

### sourceOrg Values (observed)

CFA, VICSES, BOM, Parks Victoria, VicRoads, ESTA, Melbourne Water, DELWP (now DEECA), Ambulance Victoria

---

## 4. Potential Future Sensors

### High Priority

| Sensor | Type | Description |
|---|---|---|
| **Incident duration** | `sensor` | Time elapsed since `created` timestamp for nearest/each incident |
| **Resources deployed** | `sensor` | Number of resources responding to incidents in zone |
| **Fire size** | `sensor` | Total hectares of active fires in zone |
| **Municipality filter** | config option | Filter incidents by LGA rather than radius |
| **Source agency breakdown** | `sensor` attr | Count of incidents per sourceOrg |

### Medium Priority

| Sensor | Type | Description |
|---|---|---|
| **Statewide alerts** | `binary_sensor` | ON when any statewide warning is active |
| **Fire Danger Rating** | `sensor` | From CFA RSS feed (`data.emergency.vic.gov.au`) |
| **Total Fire Ban** | `binary_sensor` | From CFA RSS feed |
| **Incident trend** | `sensor` attr | Increasing/decreasing/stable incident count over last N updates |
| **Per-incident sensors** | `sensor` | Individual sensor per tracked incident (like weather station entities) |

### Lower Priority

| Sensor | Type | Description |
|---|---|---|
| **Region/district filter** | config option | Filter by CFA district or EMV region |
| **Incident age alert** | `binary_sensor` | ON when any incident has been active > X hours |
| **Photo integration** | card feature | Display incident photos from `photoUrl` |
| **CAP-AU compliance** | feature | Common Alerting Protocol fields for standards-compliant integration |

---

## 5. Potential Future Features

### Card Enhancements

- **Custom map markers**: Use category-specific icons on map pins (requires custom map card, not possible with native HA map)
- **Incident detail popup**: Tap an incident in the list to show full description, resources, size
- **Timeline view**: Show incident history over time
- **Severity colour on map**: Colour-coded pins by warning level
- **Sound alerts**: Audio notification via ABC 774 stream integration

### Integration Enhancements

- **Multiple feed sources**: Combine VicEmergency with CFA Total Fire Ban and BOM weather warnings
- **Automation blueprints**: Pre-built automations for common scenarios (e.g. "alert when fire within 5km", "turn on sprinklers when fire warning")
- **Notification templates**: Pre-formatted notifications with incident details
- **Historical data**: Track and graph incident counts over time via HA statistics
- **Include/exclude feedtypes**: Config option to control which feedtypes are shown (currently `burn-area` is hardcoded as excluded)

### Additional Data Sources

| Source | URL | Data available |
|---|---|---|
| CFA Incidents RSS | `data.emergency.vic.gov.au/Show?pageId=getIncidentRSS` | Incidents in RSS 2.0 format |
| CFA Fire Danger RSS | `news.cfa.vic.gov.au/CFA/CFARSS.aspx?FolderId=302,304` | Fire danger ratings, total fire bans |
| BOM Weather Warnings | `reg.bom.gov.au/fwo/IDV*` | Bureau of Meteorology warnings for Victoria |
| VicRoads Closures | Various | Road closure data |
| Melbourne Water | Various | Flood levels and river gauges |

---

## 6. Attribution Requirements

Per [EMV Emergency Data licence terms](https://www.emv.vic.gov.au/responsibilities/victorias-warning-system/emergency-data):

1. Source must be identified as "State of Victoria, Australia"
2. Must include a link to the EMV emergency data page
3. Must display the last date and time an update was received from the data feed

The integration satisfies these via the `attribution` entity attribute and the `feed_status` sensor's `last_update` tracking.

---

## 7. Related Projects & References

| Resource | URL |
|---|---|
| EMV Emergency Data | https://www.emv.vic.gov.au/responsibilities/victorias-warning-system/emergency-data |
| VicEmergency Data Feed FAQ | https://support.emergency.vic.gov.au/hc/en-gb/articles/235717508 |
| CFA RSS Feeds | https://www.cfa.vic.gov.au/rss-feeds |
| VicEmergency ArcGIS Service | https://www.arcgis.com/home/item.html?id=fe1acc1681024335b7abeb77c0a700a1 |
| aio-geojson-vicemergency-incidents | https://pypi.org/project/aio-geojson-vicemergency-incidents/ |
| Victorian Gov API Portal | https://www.vic.gov.au/api-developer-portal |
| Postman API Collection | https://www.postman.com/postman/australian-government-emergency-hazards-warnings-apis |
| HA GeoJSON Events integration | https://www.home-assistant.io/integrations/geo_json_events/ |
| Common Alerting Protocol AU | https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.html |

---

*Last updated: March 2026 — v1.2.0*
