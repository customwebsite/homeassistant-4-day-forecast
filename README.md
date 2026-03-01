# VicEmergency Incidents for Home Assistant

[![HACS Validation](https://github.com/customwebsite/vicemergency-ha/actions/workflows/hacs-validate.yml/badge.svg)](https://github.com/customwebsite/vicemergency-ha/actions/workflows/hacs-validate.yml)
[![Hassfest](https://github.com/customwebsite/vicemergency-ha/actions/workflows/hassfest.yml/badge.svg)](https://github.com/customwebsite/vicemergency-ha/actions/workflows/hassfest.yml)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=customwebsite&repository=vicemergency-ha&category=integration)

Monitor Victorian emergency incidents and warnings in Home Assistant using the official [VicEmergency](https://emergency.vic.gov.au) GeoJSON data feed.

Track fires, floods, storms, transport incidents, hazmat events, and service outages within a configurable radius of any location in Victoria, Australia. Incidents appear as entities you can use in automations, notifications, and dashboards.

---

## Features

- **Map-based zone setup** — interactive map with draggable pin and radius overlay (no manual coordinates)
- **Live incident tracking** — incidents appear on the HA map as geo-location entities
- **6 category groups** — Fire, Flood, Storm & Weather, Transport, Hazmat & Health, Outages & Closures
- **Binary alert sensors** — ON/OFF per category group for simple automations
- **Summary sensors** — total count, per-group counts, nearest incident distance, highest warning level
- **Custom events** — `vicemergency_incident_new`, `_updated`, `_removed` for advanced automations
- **Three-tier feed fallback** — GeoJSON → JSON → XML with automatic recovery
- **Feed health monitoring** — diagnostic sensor shows ok/degraded/failed status
- **Multi-zone support** — monitor multiple locations with independent settings
- **Australian Warning System** — tracks Advice, Watch & Act, and Emergency Warning levels
- **Zero dependencies** — uses only HA built-in libraries, works on all installation types

---

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=customwebsite&repository=vicemergency-ha&category=integration)

1. Click the badge above, or go to **HACS → Integrations → ⋮ → Custom Repositories**
2. Add `https://github.com/customwebsite/vicemergency-ha` as an **Integration**
3. Search for "VicEmergency" in HACS and download it
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration → VicEmergency**

### Manual

1. Download the latest release from [GitHub](https://github.com/customwebsite/vicemergency-ha/releases)
2. Copy the `custom_components/vicemergency` folder to your `config/custom_components/` directory
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration → VicEmergency**

---

## Configuration

### Setup (Config Flow)

When adding the integration you'll see an interactive map centred on your Home Assistant location:

- **Zone name** — a friendly name for this monitoring zone (e.g. "Home", "Work", "Farm")
- **Location** — drag the pin and adjust the radius to define your monitoring area

The integration tests connectivity to the VicEmergency feed before completing setup.

### Options

After setup, you can adjust these settings via **Settings → Devices & Services → VicEmergency → Configure**:

| Option | Default | Description |
|---|---|---|
| Update interval | 300s (5 min) | How often to poll the feed (minimum 120s) |
| Exclude categories | None | Category groups to ignore |
| Include statewide | Yes | Whether to include incidents flagged as statewide |

---

## Entities

Each zone creates the following entities, grouped under a single device:

### Sensors

| Entity | Description |
|---|---|
| `sensor.vicemergency_*_total_incidents` | Total active incidents in zone |
| `sensor.vicemergency_*_fire_incidents` | Count of fire incidents |
| `sensor.vicemergency_*_flood_incidents` | Count of flood incidents |
| `sensor.vicemergency_*_storm_weather_incidents` | Count of storm/weather incidents |
| `sensor.vicemergency_*_transport_incidents` | Count of transport incidents |
| `sensor.vicemergency_*_hazmat_health_incidents` | Count of hazmat/health incidents |
| `sensor.vicemergency_*_outages_closures_incidents` | Count of outage/closure incidents |
| `sensor.vicemergency_*_highest_warning` | Highest warning level (none/advice/watch_and_act/emergency_warning) |
| `sensor.vicemergency_*_nearest_incident` | Distance to nearest incident (km) |
| `sensor.vicemergency_*_feed_status` | Feed health: ok, degraded, or failed (diagnostic) |

### Binary Sensors

| Entity | ON when |
|---|---|
| `binary_sensor.vicemergency_*_fire_active` | Any fire incident in zone |
| `binary_sensor.vicemergency_*_flood_active` | Any flood incident in zone |
| `binary_sensor.vicemergency_*_storm_weather_active` | Any storm/weather incident in zone |
| `binary_sensor.vicemergency_*_transport_active` | Any transport incident in zone |
| `binary_sensor.vicemergency_*_hazmat_health_active` | Any hazmat/health incident in zone |
| `binary_sensor.vicemergency_*_outages_closures_active` | Any outage/closure incident in zone |

### Geo-Location Entities

Each active incident within the zone radius creates a `geo_location` entity that:
- Appears on the Home Assistant map
- Shows distance from zone centre
- Includes full incident details as attributes
- Is automatically removed when the incident ends

---

## Dashboard Examples

### Summary card only

```yaml
type: custom:vicemergency-card
entity: sensor.vicemergency_home_total_incidents
```

### Summary card with auto-showing map

The map appears only when there are active incidents and hides when all clear:

```yaml
type: vertical-stack
cards:
  - type: custom:vicemergency-card
    entity: sensor.vicemergency_home_total_incidents
  - type: conditional
    conditions:
      - entity: sensor.vicemergency_home_total_incidents
        state_not: "0"
    card:
      type: map
      geo_location_sources:
        - vicemergency
      default_zoom: 10
      hours_to_show: 0
```

### Compact mode (no incident list)

```yaml
type: custom:vicemergency-card
entity: sensor.vicemergency_home_total_incidents
compact: true
```

---

## Automations

### Alert when a new fire starts nearby

```yaml
automation:
  - alias: "VicEmergency - New fire alert"
    trigger:
      - platform: event
        event_type: vicemergency_incident_new
        event_data:
          category_group: fire
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.distance_km < 20 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "🔥 New fire near {{ trigger.event.data.zone }}"
          message: >
            {{ trigger.event.data.source_title }}
            {{ trigger.event.data.distance_km }}km {{ trigger.event.data.bearing }}
            Status: {{ trigger.event.data.status }}
```

### Alert when warning level escalates

```yaml
automation:
  - alias: "VicEmergency - Emergency warning"
    trigger:
      - platform: state
        entity_id: sensor.vicemergency_home_highest_warning
        to: "emergency_warning"
    action:
      - service: notify.mobile_app
        data:
          title: "🚨 Emergency Warning"
          message: "An Emergency Warning has been issued in your area. Check emergency.vic.gov.au immediately."
          data:
            push:
              sound:
                name: default
                critical: 1
                volume: 1.0
```

### Alert when feed is degraded

```yaml
automation:
  - alias: "VicEmergency - Feed degraded"
    trigger:
      - platform: state
        entity_id: sensor.vicemergency_home_feed_status
        to: "degraded"
        for:
          hours: 2
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ VicEmergency feed degraded"
          message: "The primary data feed has been unavailable for 2 hours. Running on fallback."
```

---

## ⚠️ Important Safety Notice

**This integration is an informational tool only.** It is not a replacement for official emergency warnings and should never be relied upon as your sole source of emergency information.

During an emergency, always:

- Visit **[emergency.vic.gov.au](https://emergency.vic.gov.au)** for official warnings and updates
- Tune in to **ABC Melbourne 774 AM** for emergency broadcasts ([listen live online](https://www.abc.net.au/listen/live/melbourne))
- Call **000** for life-threatening emergencies
- Follow instructions from emergency services personnel
- Monitor the **VicEmergency app** on your mobile device

Data feeds may be delayed, incomplete, or unavailable during major events. Sensor and card states may not reflect the current situation on the ground. Always verify critical information through official channels before making safety decisions.

---

## Data Source

This integration uses the official VicEmergency GeoJSON feed at `emergency.vic.gov.au/public/osom-geojson.json`, published by Emergency Management Victoria under Creative Commons Attribution 3.0 Australia.

The feed aggregates incidents from 9 source agencies including CFA, VICSES, BOM, Parks Victoria, VicRoads, ESTA, Melbourne Water, DELWP, and Ambulance Victoria.

### Fallback Chain

If the primary GeoJSON endpoint fails:

1. **Primary:** `emergency.vic.gov.au/public/osom-geojson.json` (full geometry)
2. **Fallback JSON:** `data.emergency.vic.gov.au/Show?pageId=getIncidentJSON` (flat lat/lon)
3. **Fallback XML:** `data.emergency.vic.gov.au/Show?pageId=getIncidentXML` (flat lat/lon)

After 3 consecutive primary failures, the integration enters sustained fallback mode and periodically retries every 10 cycles to auto-recover.

### References

- [EMV Emergency Data & Licence Terms](https://www.emv.vic.gov.au/responsibilities/victorias-warning-system/emergency-data) — data usage conditions and Creative Commons Attribution 3.0 Australia licence
- [VicEmergency Data Feed FAQ](https://support.emergency.vic.gov.au/hc/en-gb/articles/235717508-How-do-I-access-the-VicEmergency-data-feed) — official feed access information
- [CFA RSS Feeds](https://www.cfa.vic.gov.au/rss-feeds) — CFA incident and fire danger data feeds
- [VicEmergency Incidents on ArcGIS](https://www.arcgis.com/home/item.html?id=fe1acc1681024335b7abeb77c0a700a1) — GeoJSON service overview
- [aio-geojson-vicemergency-incidents](https://pypi.org/project/aio-geojson-vicemergency-incidents/) — community Python library for VicEmergency GeoJSON feeds
- [Victorian Government API Developer Portal](https://www.vic.gov.au/api-developer-portal) — government APIs and developer resources

---

## Category Groups

| Group | Example incident types |
|---|---|
| 🔥 Fire | Bushfire, Planned Burn, Burn Area, Burn Advice |
| 🌊 Flood | Flood, Riverine Flood, Flash Flood, Coastal Flood, Dam Failure |
| ⛈️ Storm & Weather | Storm, Severe Storm, Severe Thunderstorm, Severe Weather, Damaging Winds, Earthquake, Tsunami, Landslide |
| 🚗 Transport | Vehicle/Aircraft/Rail/Marine Accident, Rescue |
| ☣️ Hazmat & Health | Hazardous Material, Medical, Shark Sighting, Water Pollution |
| 🚧 Outages & Closures | Power/Gas/Water Outage, Road Closed, School/Beach/Park Closure |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

Data sourced from the State of Victoria under [Creative Commons Attribution 3.0 Australia](https://creativecommons.org/licenses/by/3.0/au/).
