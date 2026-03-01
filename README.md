# CFA Fire Danger Forecast for Home Assistant

[![HACS Validation](https://github.com/customwebsite/homeassistant-4-day-forecast/actions/workflows/hacs-validate.yml/badge.svg)](https://github.com/customwebsite/homeassistant-4-day-forecast/actions/workflows/hacs-validate.yml)
[![Hassfest](https://github.com/customwebsite/homeassistant-4-day-forecast/actions/workflows/hassfest.yml/badge.svg)](https://github.com/customwebsite/homeassistant-4-day-forecast/actions/workflows/hassfest.yml)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=customwebsite&repository=homeassistant-4-day-forecast&category=integration)

A Home Assistant custom integration that provides **fire danger ratings** and **Total Fire Ban** status for all CFA (Country Fire Authority) fire districts across Victoria, Australia. Use it to plan your week — know which days carry elevated fire risk so you can prepare your property, adjust travel plans, and schedule outdoor activities accordingly.

Data is sourced from the official [CFA RSS feeds](https://www.cfa.vic.gov.au/rss-feeds), using the AFDRS (Australian Fire Danger Rating System) colour standard.

---

## Features

- **4-day fire danger forecast** — Today, Tomorrow, Day 3, Day 4 (configurable 1–4 days)
- **Total Fire Ban detection** — district-specific with statewide declaration support
- **All 9 CFA fire districts** supported
- **Max Severity sensor** — highest rating across all forecast days (great for automations)
- **Feed Status diagnostic sensor** — monitors CFA data feed health
- **Combined feed with fallback** — single HTTP request for all districts, automatic fallback to individual feeds on failure
- **AFDRS-compliant colours** — Moderate=green, High=yellow, Extreme=orange, Catastrophic=red
- **Rating-specific icons** — visual differentiation per severity level
- **Lovelace card auto-registration** — card works immediately after install, no manual resource URL needed
- **Stale entity cleanup** — orphaned entities removed automatically on config changes
- **UI-based configuration** via Config Flow (no YAML required)
- **Configurable update interval** (default: 30 minutes)

## Sensors Created

For each configured district, the integration creates **10 sensors**:

| Sensor | Example Entity ID | State |
|---|---|---|
| Fire Danger Rating Today | `sensor.cfa_central_fire_district_fire_danger_rating_today` | `MODERATE` |
| Fire Danger Rating Tomorrow | `sensor.cfa_central_fire_district_fire_danger_rating_tomorrow` | `HIGH` |
| Fire Danger Rating Day 3 | `sensor.cfa_central_fire_district_fire_danger_rating_day_3` | `EXTREME` |
| Fire Danger Rating Day 4 | `sensor.cfa_central_fire_district_fire_danger_rating_day_4` | `NO RATING` |
| Total Fire Ban Today | `sensor.cfa_central_fire_district_total_fire_ban_today` | `Yes` / `No` |
| Total Fire Ban Tomorrow | `sensor.cfa_central_fire_district_total_fire_ban_tomorrow` | `Yes` / `No` |
| Total Fire Ban Day 3 | `sensor.cfa_central_fire_district_total_fire_ban_day_3` | `Yes` / `No` |
| Total Fire Ban Day 4 | `sensor.cfa_central_fire_district_total_fire_ban_day_4` | `Yes` / `No` |
| Max Fire Danger Rating | `sensor.cfa_central_fire_district_max_fire_danger_rating` | `EXTREME` |
| Feed Status | `sensor.cfa_central_fire_district_feed_status` | `ok` / `degraded` / `failed` |

The number of rating and TFB sensors depends on the **Forecast days** setting (1–4, default 4).

### Sensor Attributes

**Fire Danger Rating sensors** include:

- `date` — Forecast date label (e.g. "Wednesday, 12 February 2026")
- `severity` — Numeric severity (0–5)
- `colour` — AFDRS hex colour for the rating
- `total_fire_ban` — Boolean TFB status for the same day
- `forecast_issued_at` — BoM forecast issue timestamp
- `feed_published` — RSS feed publication time

**Max Severity sensor** includes:

- `severity` — Numeric severity of the worst day
- `colour` — Hex colour for the worst rating
- `any_total_fire_ban` — True if any day has a TFB
- `worst_day` — Date label of the worst day
- `forecast_days` — Number of forecast days available
- `feed_source` — `combined` or `individual` (which feed strategy was used)

**Feed Status sensor** (diagnostic) includes:

- `feed_source` — `combined` or `individual`
- `combined_failures` — Consecutive combined-feed failure count
- `fallback_active` — True when in sustained fallback mode (3+ consecutive combined failures)
- `failed_districts` — List of district slugs that failed (if any)
- `last_error` — Error message from the most recent failure
- `last_successful_update` — ISO timestamp of the last successful data fetch

## Feed Resilience

The integration uses a two-tier fetching strategy:

1. **Primary**: Combined RSS feed — a single HTTP request returns data for all 9 districts
2. **Fallback**: Individual per-district RSS feeds — one request per district, fetched concurrently

If the combined feed fails, the integration automatically falls back to individual feeds. After 3 consecutive combined-feed failures, it enters sustained fallback mode (skipping the combined feed timeout) and periodically retries to auto-recover. Individual feed failures are isolated — if one district's feed is down, the others continue updating.

The Feed Status diagnostic sensor and the Lovelace card's status indicator make this visible without checking logs.

## Lovelace Card

A custom card is included and auto-registered on install. To use it:

```yaml
type: custom:cfa-fire-forecast-card
title: Fire Danger Forecast
districts:
  - slug: central
    name: Central
```

For multiple districts:

```yaml
type: custom:cfa-fire-forecast-card
title: Fire Danger Forecast
districts:
  - slug: central
    name: Central
  - slug: north-east
    name: North East
  - slug: east-gippsland
    name: East Gippsland
```

Card options:

- `title` — Card header text (default: "Fire Danger Forecast")
- `show_title` — Set to `false` to hide the header
- `districts` — List of districts with `slug` and optional `name`

The card displays a subtle feed health indicator dot in the footer: green (ok), amber (degraded/fallback), or red (failed).

### Dashboard Example — Conditional Fire Danger Card

Show the fire danger card only when the rating is HIGH or above:

```yaml
type: conditional
conditions:
  - entity: sensor.cfa_central_fire_district_max_fire_danger_rating
    state_not: "NO RATING"
    state_not: "LOW-MODERATE"
    state_not: "MODERATE"
card:
  type: custom:cfa-fire-forecast-card
  title: ⚠️ Elevated Fire Danger
  districts:
    - slug: central
      name: Central
```

### Dashboard Example — TFB Planning Banner

```yaml
type: conditional
conditions:
  - entity: sensor.cfa_central_fire_district_total_fire_ban_tomorrow
    state: "Yes"
card:
  type: markdown
  content: >
    ## 🚫 Total Fire Ban Tomorrow
    A Total Fire Ban has been declared for tomorrow in the Central fire district.
    Plan accordingly — no fires may be lit in the open. Check
    [CFA](https://www.cfa.vic.gov.au/warnings-restrictions/total-fire-bans-and-ratings)
    for details and exemptions.
```

## Supported Districts

| District Slug | Display Name |
|---|---|
| `central` | Central |
| `north-central` | North Central |
| `south-west` | South West |
| `northern-country` | Northern Country |
| `north-east` | North East |
| `mallee` | Mallee |
| `wimmera` | Wimmera |
| `east-gippsland` | East Gippsland |
| `west-and-south-gippsland` | West & South Gippsland |

You can add multiple districts — each creates its own set of sensors. All districts share a single HTTP request to the combined feed.

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=customwebsite&repository=homeassistant-4-day-forecast&category=integration)

1. Click the badge above, or go to **HACS → Integrations → ⋮ → Custom Repositories**
2. Add `https://github.com/customwebsite/homeassistant-4-day-forecast` as an **Integration**
3. Search for "CFA Fire Danger Forecast" and install it
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration → CFA Fire Danger Forecast**

### Manual

1. Download the [latest release](https://github.com/customwebsite/homeassistant-4-day-forecast/releases/latest) zip or clone the repository
2. Copy the following into your Home Assistant `config/` directory:

   ```
   config/
   ├── custom_components/
   │   └── cfa_fire_forecast/        ← copy this entire folder
   │       ├── www/
   │       │   └── cfa-fire-forecast-card.js
   │       ├── translations/
   │       │   └── en.json
   │       ├── __init__.py
   │       ├── config_flow.py
   │       ├── const.py
   │       ├── coordinator.py
   │       ├── manifest.json
   │       ├── sensor.py
   │       └── strings.json
   └── www/                           ← copy this folder (Lovelace card fallback)
       └── cfa-fire-forecast-card.js
   ```

   The `custom_components/cfa_fire_forecast/` folder is required. The `www/` folder at the root is a fallback for the Lovelace card — the integration will attempt to auto-register the card from its own `www/` subfolder, but having it in `config/www/` ensures it works if auto-registration fails.
3. Restart Home Assistant
4. If the Lovelace card doesn't auto-register, add it manually: **Settings → Dashboards → three dots → Resources → Add Resource** with URL `/local/cfa-fire-forecast-card.js` and type **JavaScript Module**

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **CFA Fire Danger Forecast**
3. Select your fire district from the dropdown
4. Done! Sensors will appear within moments

### Options

After adding the integration, click **Configure** on the integration page to adjust:

- **Update interval** — How often to poll the CFA feed (300–86400 seconds, default 1800)
- **Forecast days** — How many days of forecast sensors to create (1–4, default 4)

## Automation Examples

### Notify on upcoming Extreme or Catastrophic rating

```yaml
automation:
  - alias: "CFA Extreme Fire Danger Ahead"
    trigger:
      - platform: state
        entity_id: sensor.cfa_central_fire_district_max_fire_danger_rating
        to:
          - "EXTREME"
          - "CATASTROPHIC"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🔥 Fire Danger Warning — Plan Ahead"
          message: >
            {{ trigger.to_state.state }} fire danger rating forecast for
            {{ state_attr(trigger.entity_id, 'worst_day') }}
            in the Central fire district.
            Review your fire plan and prepare your property.
```

### Notify on Total Fire Ban declared

```yaml
automation:
  - alias: "CFA Total Fire Ban Alert"
    trigger:
      - platform: state
        entity_id: sensor.cfa_central_fire_district_total_fire_ban_today
        to: "Yes"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚫 Total Fire Ban Today"
          message: "A Total Fire Ban is in effect today for the Central fire district."
```

### Notify on feed problems

```yaml
automation:
  - alias: "CFA Feed Problem Alert"
    trigger:
      - platform: state
        entity_id: sensor.cfa_central_fire_district_feed_status
        to: "failed"
        for: "02:00:00"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "⚠️ CFA Feed Issue"
          message: >
            CFA fire data feed has been unavailable for 2 hours.
            Fire danger ratings may be stale.
```

---

## ⚠️ Important Safety Notice

**This integration is a planning tool only.** It provides forecast fire danger ratings to help you prepare for the days ahead — it is not a replacement for official emergency warnings and should never be relied upon as your sole source of fire safety information.

Use this integration to:

- Plan property preparation and maintenance ahead of high-risk days
- Schedule or reschedule outdoor activities around fire danger forecasts
- Know when Total Fire Bans are coming so you can adjust plans in advance
- Build awareness of fire danger trends across the week

During a fire emergency, always:

- Visit the **[CFA website](https://www.cfa.vic.gov.au/warnings-restrictions/total-fire-bans-and-ratings)** for official fire danger ratings and restrictions
- Visit **[emergency.vic.gov.au](https://emergency.vic.gov.au)** for live incident warnings and updates
- Tune in to **ABC Melbourne 774 AM** for emergency broadcasts ([listen live online](https://www.abc.net.au/listen/live/melbourne))
- Call **000** for life-threatening emergencies
- Call the **VicEmergency Hotline** on **1800 226 226**
- Monitor the **VicEmergency app** on your mobile device
- Follow instructions from CFA and emergency services personnel

Data feeds may be delayed, incomplete, or unavailable during major events. Sensor and card states may not reflect the current situation on the ground. Always verify critical information through official channels before making safety decisions.

---

## Fire Danger Ratings (AFDRS)

| Rating | Severity | Colour | Icon |
|---|---|---|---|
| NO RATING | 0 | Grey | `mdi:shield-check` |
| LOW-MODERATE | 1 | Light Green | `mdi:fire` |
| MODERATE | 2 | Green | `mdi:fire` |
| HIGH | 3 | Yellow | `mdi:fire-alert` |
| EXTREME | 4 | Orange | `mdi:alert-octagon` |
| CATASTROPHIC | 5 | Red | `mdi:skull-crossbones` |

Colours follow the official Australian Fire Danger Rating System (AFDRS) introduced in September 2022.

---

## Data Source

Data is fetched from the official CFA RSS feeds:

- **Combined feed** (primary): `https://www.cfa.vic.gov.au/cfa/rssfeed/tfbfdrforecast_rss.xml`
- **Individual feeds** (fallback): `https://www.cfa.vic.gov.au/cfa/rssfeed/{district}-firedistrict_rss.xml`

### References

- [CFA Total Fire Bans & Ratings](https://www.cfa.vic.gov.au/warnings-restrictions/total-fire-bans-and-ratings) — official fire danger ratings page
- [CFA RSS Feeds](https://www.cfa.vic.gov.au/rss-feeds) — data feed documentation
- [Australian Fire Danger Rating System (AFDRS)](https://www.afac.com.au/initiative/afdrs) — national rating system specification
- [EMV Emergency Data & Licence Terms](https://www.emv.vic.gov.au/responsibilities/victorias-warning-system/emergency-data) — Victorian emergency data usage conditions
- [Bureau of Meteorology Fire Weather Services](http://www.bom.gov.au/weather-services/fire-weather-centre/index.shtml) — BoM fire weather forecasts for Victoria

---

## Credits

- **Data Source**: [Country Fire Authority (CFA)](https://www.cfa.vic.gov.au/) Victoria, Australia
- **Original WordPress Plugin**: [cfa-4-day-forecast](https://github.com/customwebsite/cfa-4-day-forecast) by Shaun Haddrill
- **Home Assistant Integration**: Adapted for HACS

## License

MIT License — see [LICENSE](LICENSE) for details.

Data sourced from the Country Fire Authority, State of Victoria, Australia. CFA data is provided under the [Creative Commons Attribution 3.0 Australia](https://creativecommons.org/licenses/by/3.0/au/) licence.
