# CFA Fire Danger Forecast for Home Assistant

[![HACS Compatible](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that provides real-time **fire danger ratings** and **Total Fire Ban** status for all CFA (Country Fire Authority) fire districts across Victoria, Australia.

Data is sourced from the official [CFA RSS feeds](https://www.cfa.vic.gov.au/rss-feeds).

---

## Features

- **4-day fire danger forecast** — Today, Tomorrow, Day 3, Day 4
- **Total Fire Ban detection** — including statewide declarations
- **All 9 CFA fire districts** supported
- **Max Severity sensor** — highest rating across all forecast days (great for automations)
- **UI-based configuration** via Config Flow (no YAML required)
- **Configurable update interval** (default: 1 hour)
- **Rich attributes** — severity level, colour, BoM issue time, feed publish date

## Sensors Created

For each configured district, the integration creates **9 sensors**:

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

### Sensor Attributes

**Fire Danger Rating sensors** include:
- `date` — Forecast date label (e.g. "Wednesday, 12 February 2026")
- `severity` — Numeric severity (0–5)
- `colour` — Official CFA hex colour for the rating
- `total_fire_ban` — Boolean TFB status for the same day
- `forecast_issued_at` — BoM forecast issue timestamp
- `feed_published` — RSS feed publication time

**Max Severity sensor** includes:
- `severity` — Numeric severity of the worst day
- `colour` — Hex colour for the worst rating
- `any_total_fire_ban` — True if any day has a TFB
- `worst_day` — Date label of the worst day
- `forecast_days` — Number of forecast days available

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

You can add multiple districts — each creates its own set of sensors.

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the **three dots** menu → **Custom repositories**
3. Add `https://github.com/customwebsite/ha-cfa-fire-forecast` as an **Integration**
4. Search for **CFA Fire Danger Forecast** and install it
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/cfa_fire_forecast` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **CFA Fire Danger Forecast**
3. Select your fire district from the dropdown
4. Done! Sensors will appear within moments

### Options

After adding the integration, click **Configure** to adjust:

- **Update interval** — How often to poll the CFA feed (300–86400 seconds, default 3600)

## Automation Examples

### Notify on Extreme or Catastrophic rating

```yaml
automation:
  - alias: "CFA Extreme Fire Danger Alert"
    trigger:
      - platform: state
        entity_id: sensor.cfa_central_fire_district_max_fire_danger_rating
        to:
          - "EXTREME"
          - "CATASTROPHIC"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🔥 Fire Danger Warning"
          message: >
            {{ trigger.to_state.state }} fire danger rating forecast for
            {{ state_attr(trigger.entity_id, 'worst_day') }}
            in the Central fire district.
```

### Notify on Total Fire Ban

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

## Fire Danger Ratings

| Rating | Severity | Colour |
|---|---|---|
| NO RATING | 0 | Grey |
| LOW-MODERATE | 1 | Green |
| MODERATE | 2 | Gold |
| HIGH | 3 | Orange |
| EXTREME | 4 | Red |
| CATASTROPHIC | 5 | Dark Red |

## Data Source

Data is fetched from the official CFA RSS feeds:
```
https://www.cfa.vic.gov.au/cfa/rssfeed/{district}-firedistrict_rss.xml
```

## Disclaimer

This information is for general reference only. Always check the [official CFA website](https://www.cfa.vic.gov.au/warnings-restrictions/total-fire-bans-and-ratings) for the most current fire danger ratings and restrictions.

**In case of fire emergency, call 000 immediately.**

## Credits

- **Data Source**: [Country Fire Authority (CFA)](https://www.cfa.vic.gov.au/) Victoria, Australia
- **Original WordPress Plugin**: [cfa-4-day-forecast](https://github.com/customwebsite/cfa-4-day-forecast) by Shaun Haddrill
- **Home Assistant Integration**: Adapted for HACS

## License

MIT License — see [LICENSE](LICENSE) for details.
