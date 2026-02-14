/**
 * CFA Fire Danger Forecast Card — Compact
 * Optimised for narrow columns (1/3 width dashboards) with 1–2 districts.
 *
 * Install: Place in config/www/cfa-fire-forecast-card.js
 * Resource: /local/cfa-fire-forecast-card.js  (JavaScript Module)
 *
 * Config:
 *   type: custom:cfa-fire-forecast-card
 *   title: Fire Danger Forecast
 *   districts:
 *     - slug: central
 *       name: Central
 */

const RATING_COLOURS = {
  "NO RATING":     { bg: "#ACACAC",  text: "#FFFFFF" },
  "LOW-MODERATE":  { bg: "#8DC44D",  text: "#FFFFFF" },
  "MODERATE":      { bg: "#4EA346",  text: "#FFFFFF" },
  "HIGH":          { bg: "#F5C518",  text: "#1a1a1a" },
  "EXTREME":       { bg: "#E55B25",  text: "#FFFFFF" },
  "CATASTROPHIC":  { bg: "#CC2200",  text: "#FFFFFF" },
  "UNKNOWN":       { bg: "#616161",  text: "#FFFFFF" },
};

const FEED_STATUS_META = {
  "ok":       { colour: "#4EA346", label: "Feed OK" },
  "degraded": { colour: "#F5A623", label: "Feed degraded \u2014 using fallback" },
  "failed":   { colour: "#CC2200", label: "Feed unavailable" },
};

const DAY_KEYS = ["today", "tomorrow", "day_3", "day_4"];

function shortDay(dateLabel, index) {
  if (index === 0) return "Today";
  if (index === 1) return "Tmrw";
  if (!dateLabel) return "Day " + (index + 1);
  const map = { monday:"Mon", tuesday:"Tue", wednesday:"Wed", thursday:"Thu", friday:"Fri", saturday:"Sat", sunday:"Sun" };
  const first = dateLabel.split(",")[0].trim().toLowerCase();
  return map[first] || dateLabel.split(",")[0].trim().slice(0, 3);
}

function shortDate(dateLabel) {
  if (!dateLabel) return "";
  try {
    const d = new Date(dateLabel);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("en-AU", { day: "numeric", month: "short" });
  } catch (_) { return ""; }
}

class CfaFireForecastCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    if (!config.districts || !Array.isArray(config.districts) || config.districts.length === 0) {
      throw new Error("Define at least one district.");
    }
    this._config = config;
  }

  getCardSize() {
    return 3 + (this._config.districts ? this._config.districts.length : 1);
  }

  _getEntities(slug) {
    if (!this._hass) return null;
    const safe = slug.replace(/-/g, "_");
    const pfx = "sensor.cfa_" + safe + "_fire_district_";
    const e = {};
    for (const key of DAY_KEYS) {
      e[key] = {
        rating: this._hass.states[pfx + "fire_danger_rating_" + key],
        tfb:    this._hass.states[pfx + "total_fire_ban_" + key],
      };
    }
    return e;
  }

  _getFeedStatus(slug) {
    if (!this._hass) return null;
    const safe = slug.replace(/-/g, "_");
    const entity_id = "sensor.cfa_" + safe + "_fire_district_feed_status";
    return this._hass.states[entity_id] || null;
  }

  _getWorstFeedStatus() {
    if (!this._config.districts) return "ok";
    var worst = "ok";
    for (var i = 0; i < this._config.districts.length; i++) {
      var s = this._getFeedStatus(this._config.districts[i].slug);
      var state = s ? s.state : "failed";
      if (state === "failed") return "failed";
      if (state === "degraded") worst = "degraded";
    }
    return worst;
  }

  _getDayHeaders() {
    if (!this._config.districts || !this._hass) return [];
    const ents = this._getEntities(this._config.districts[0].slug);
    if (!ents) return [];
    return DAY_KEYS.map(function(key, i) {
      var s = ents[key] && ents[key].rating;
      var dateLabel = (s && s.attributes && s.attributes.date) || "";
      return { label: shortDay(dateLabel, i), date: shortDate(dateLabel), isToday: i === 0 };
    });
  }

  _render() {
    if (!this._hass || !this._config.districts) return;
    var headers = this._getDayHeaders();
    var title = this._config.title || "Fire Danger Forecast";
    var showTitle = this._config.show_title !== false;
    var single = this._config.districts.length === 1;
    var feedStatus = this._getWorstFeedStatus();
    var fsMeta = FEED_STATUS_META[feedStatus] || FEED_STATUS_META["ok"];

    var h = '<style>' + this._css(single) + '</style><ha-card>';

    if (showTitle) h += '<div class="title">' + title + '</div>';

    h += '<div class="wrap"><table><thead><tr>';
    if (!single) h += '<th class="dh">District</th>';
    for (var i = 0; i < headers.length; i++) {
      var hd = headers[i];
      h += '<th class="dayh">'
        + (hd.isToday ? '<b class="tb">TODAY</b>' : '')
        + '<span class="dl">' + hd.label + '</span>'
        + '<span class="dd">' + hd.date + '</span></th>';
    }
    h += '</tr></thead><tbody>';

    for (var d = 0; d < this._config.districts.length; d++) {
      var dist = this._config.districts[d];
      var ents = this._getEntities(dist.slug);
      var name = dist.name || dist.slug.replace(/-/g, " ").replace(/\b\w/g, function(c) { return c.toUpperCase(); });
      h += '<tr>';
      if (!single) h += '<td class="dn">' + name + '</td>';
      for (var k = 0; k < DAY_KEYS.length; k++) {
        var key = DAY_KEYS[k];
        var rating = (ents && ents[key] && ents[key].rating && ents[key].rating.state) || "UNKNOWN";
        var tfb = ents && ents[key] && ents[key].tfb && ents[key].tfb.state === "Yes";
        var c = RATING_COLOURS[rating] || RATING_COLOURS["UNKNOWN"];
        h += '<td class="rc">'
          + '<div class="pill" style="background:' + c.bg + ';color:' + c.text + '">' + rating + '</div>'
          + (tfb ? '<div class="tfb">\uD83D\uDD25 TFB</div>' : '')
          + '</td>';
      }
      h += '</tr>';
    }

    h += '</tbody></table></div>';

    // Footer with feed status indicator
    h += '<div class="ft">'
      + '<span class="fs-dot" style="background:' + fsMeta.colour + '" title="' + fsMeta.label + '"></span>'
      + (feedStatus !== "ok" ? '<span class="fs-label">' + fsMeta.label + '</span> \u00b7 ' : '')
      + 'Data from <a href="https://www.cfa.vic.gov.au/warnings-restrictions/total-fire-bans-and-ratings" target="_blank" rel="noopener">CFA Victoria</a>'
      + '</div>';

    h += '</ha-card>';
    this.shadowRoot.innerHTML = h;
  }

  _css(single) {
    return '\
      :host {\
        --navy: #002855;\
        --navy-lt: #1a4480;\
        --navy-dk: #001a3a;\
        --gold: #F5A623;\
        --bg: var(--ha-card-background, #f4f6f9);\
        --bg2: #eef1f6;\
        --bdr: #d0d7e2;\
      }\
      ha-card {\
        overflow: hidden;\
        border-radius: 10px;\
        background: var(--bg);\
        border: 1px solid var(--bdr);\
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;\
      }\
      .title {\
        background: var(--navy-dk);\
        color: #fff;\
        font-size: 12px;\
        font-weight: 700;\
        letter-spacing: .5px;\
        padding: 8px 12px;\
        text-transform: uppercase;\
      }\
      .wrap { overflow-x: auto; }\
      table { width: 100%; border-collapse: collapse; table-layout: fixed; }\
      \
      thead th {\
        background: var(--navy);\
        color: #fff;\
        padding: 6px 3px 8px;\
        text-align: center;\
        vertical-align: middle;\
        border-right: 1px solid var(--navy-lt);\
      }\
      thead th:last-child { border-right: none; }\
      .dh {\
        text-align: left;\
        padding-left: 8px;\
        font-size: 10px;\
        font-weight: 700;\
        white-space: nowrap;\
      }\
      .dayh { min-width: 0; }\
      .dl { display: block; font-size: 11px; font-weight: 700; line-height: 1.2; }\
      .dd { display: block; font-size: 9px; font-weight: 400; opacity: .65; margin-top: 1px; }\
      .tb {\
        display: inline-block;\
        background: var(--gold);\
        color: var(--navy-dk);\
        font-size: 7px;\
        font-weight: 800;\
        letter-spacing: .5px;\
        padding: 1px 4px;\
        border-radius: 2px;\
        margin-bottom: 2px;\
        line-height: 1.4;\
      }\
      \
      tbody tr { border-bottom: 1px solid var(--bdr); }\
      tbody tr:nth-child(even) { background: var(--bg2); }\
      tbody tr:last-child { border-bottom: none; }\
      .dn {\
        padding: 8px;\
        font-size: 11px;\
        font-weight: 700;\
        color: var(--navy-dk);\
        white-space: nowrap;\
      }\
      .rc {\
        padding: ' + (single ? '10px 4px' : '8px 3px') + ';\
        text-align: center;\
        vertical-align: middle;\
      }\
      \
      .pill {\
        display: block;\
        margin: 0 auto;\
        padding: ' + (single ? '8px 2px' : '6px 2px') + ';\
        border-radius: 4px;\
        font-size: ' + (single ? '11px' : '9px') + ';\
        font-weight: 800;\
        letter-spacing: .3px;\
        text-transform: uppercase;\
        text-align: center;\
        box-shadow: 0 1px 3px rgba(0,0,0,.15);\
      }\
      \
      .tfb {\
        margin-top: 5px;\
        display: inline-block;\
        background: #B71C1C;\
        color: #fff;\
        font-size: 8px;\
        font-weight: 800;\
        letter-spacing: .5px;\
        padding: 2px 5px;\
        border-radius: 3px;\
        animation: blink 1s ease-in-out infinite;\
        box-shadow: 0 0 6px rgba(183,28,28,.5);\
      }\
      @keyframes blink {\
        0%,100% { opacity:1; box-shadow: 0 0 6px rgba(183,28,28,.5); }\
        50%     { opacity:.3; box-shadow: 0 0 16px rgba(183,28,28,.9); }\
      }\
      \
      .ft {\
        padding: 4px 10px 5px;\
        font-size: 8px;\
        color: #8a90a0;\
        text-align: right;\
        display: flex;\
        align-items: center;\
        justify-content: flex-end;\
        gap: 4px;\
      }\
      .ft a { color: var(--navy-lt); text-decoration: none; }\
      .ft a:hover { text-decoration: underline; }\
      .fs-dot {\
        display: inline-block;\
        width: 6px;\
        height: 6px;\
        border-radius: 50%;\
        flex-shrink: 0;\
        cursor: help;\
      }\
      .fs-label {\
        color: #a08050;\
        font-weight: 600;\
      }\
    ';
  }

  static getStubConfig() {
    return {
      title: "Fire Danger Forecast",
      districts: [{ slug: "central", name: "Central" }],
    };
  }
}

customElements.define("cfa-fire-forecast-card", CfaFireForecastCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "cfa-fire-forecast-card",
  name: "CFA Fire Danger Forecast",
  description: "Compact CFA fire danger ratings table with flashing Total Fire Ban indicators.",
  preview: true,
});

console.info(
  "%c CFA-FIRE-FORECAST %c v1.1.0-compact ",
  "color:#FFF;background:#002855;padding:2px 5px;border-radius:3px 0 0 3px;font-weight:bold",
  "color:#002855;background:#F5A623;padding:2px 5px;border-radius:0 3px 3px 0;font-weight:bold"
);
