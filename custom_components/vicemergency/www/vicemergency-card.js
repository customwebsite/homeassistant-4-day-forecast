/**
 * VicEmergency Card for Home Assistant
 * 
 * Custom Lovelace card displaying emergency incidents from the
 * VicEmergency integration with warning level indicators, category
 * breakdowns, and a scrollable incident list.
 *
 * Configuration:
 *   type: custom:vicemergency-card
 *   entity: sensor.vicemergency_home_total_incidents
 *   title: VicEmergency          # optional
 *   max_incidents: 10            # optional
 *   compact: false               # optional — hides incident list
 *   show_map_link: true          # optional
 *
 * @version 1.2.0
 */

const CARD_VERSION = "1.0.0";

console.info(
  `%c VICEMERGENCY %c v${CARD_VERSION} `,
  "color: white; background: #CC0000; font-weight: 700; padding: 2px 6px; border-radius: 4px 0 0 4px;",
  "color: #CC0000; background: #f5f5f5; font-weight: 700; padding: 2px 6px; border-radius: 0 4px 4px 0;"
);

// ───────────────────────────────────────────────────────────────
// Constants
// ───────────────────────────────────────────────────────────────

const WARNING_META = {
  none:              { label: "All Clear",          colour: "#4CAF50", bg: "rgba(76,175,80,0.08)",  icon: "mdi:check-circle" },
  active:            { label: "Active",             colour: "#78909C", bg: "rgba(120,144,156,0.08)", icon: "mdi:alert-circle-outline" },
  advice:            { label: "Advice",             colour: "#FFC107", bg: "rgba(255,193,7,0.08)",  icon: "mdi:information" },
  watch_and_act:     { label: "Watch & Act",        colour: "#FF6D00", bg: "rgba(255,109,0,0.08)",  icon: "mdi:alert" },
  emergency_warning: { label: "Emergency Warning",  colour: "#D50000", bg: "rgba(213,0,0,0.08)",    icon: "mdi:alert-octagon" },
};

const GROUP_META = {
  fire:             { label: "Fire",              icon: "mdi:fire",              colour: "#E53935" },
  flood:            { label: "Flood",             icon: "mdi:flood",             colour: "#1E88E5" },
  storm_weather:    { label: "Storm",             icon: "mdi:weather-lightning", colour: "#7E57C2" },
  transport:        { label: "Transport",         icon: "mdi:car-emergency",     colour: "#FB8C00" },
  hazmat_health:    { label: "Hazmat",            icon: "mdi:biohazard",         colour: "#43A047" },
  outages_closures: { label: "Outages",           icon: "mdi:flash-off",         colour: "#757575" },
};

const FEEDTYPE_META = {
  incident:            { label: "Incident",          dot: "#78909C" },
  warning:             { label: "Advice",            dot: "#FFC107" },
  "watch-and-act":     { label: "Watch & Act",       dot: "#FF6D00" },
  "emergency-warning": { label: "Emergency Warning", dot: "#D50000" },
};

// ───────────────────────────────────────────────────────────────
// Card element
// ───────────────────────────────────────────────────────────────

class VicEmergencyCard extends HTMLElement {

  static getConfigElement() {
    return document.createElement("vicemergency-card-editor");
  }

  static getStubConfig() {
    return { entity: "", title: "VicEmergency", show_map_link: true, max_incidents: 10 };
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    this._render();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an 'entity' (total incidents sensor)");
    }
    this._config = {
      title: "VicEmergency",
      show_map_link: true,
      max_incidents: 10,
      compact: false,
      ...config,
    };
    if (this._hass) this._render();
  }

  getCardSize() {
    return this._config?.compact ? 3 : 5;
  }

  // ─── Rendering ───────────────────────────────────────────────

  _render() {
    if (!this._config || !this._hass) return;

    const entityId = this._config.entity;
    const state = this._hass.states[entityId];

    if (!state) {
      this._renderError(`Entity not found: ${entityId}`);
      return;
    }

    // Derive the entry prefix from the entity id
    // e.g. sensor.vicemergency_home_total_incidents -> vicemergency_home
    const prefix = entityId.replace("sensor.", "").replace("_total_incidents", "");

    // Gather all related entities
    const data = this._gatherData(prefix, state);

    // Build card HTML — override "none" with "active" when incidents exist
    const badgeLevel = (data.warningLevel === "none" && data.total > 0) ? "active" : data.warningLevel;
    const warning = WARNING_META[badgeLevel] || WARNING_META.none;

    this.innerHTML = `
      <ha-card>
        <style>${this._styles()}</style>
        <div class="ve-card">
          ${this._renderHeader(data, warning)}
          ${this._renderCategoryBar(data)}
          ${this._config.compact ? "" : this._renderIncidentList(data)}
          ${this._renderFooter(data)}
        </div>
      </ha-card>
    `;
  }

  _gatherData(prefix, totalState) {
    const s = this._hass.states;
    const val = (suffix) => s[`sensor.${prefix}_${suffix}`];
    const bval = (suffix) => s[`binary_sensor.${prefix}_${suffix}`];

    // Group counts
    const groups = {};
    for (const key of Object.keys(GROUP_META)) {
      const entity = val(`${key}_incidents`);
      const count = entity ? parseInt(entity.state, 10) || 0 : 0;
      groups[key] = {
        count,
        active: bval(`${key}_active`)?.state === "on",
        incidents: entity?.attributes?.incidents || [],
      };
    }

    // Warning level
    const warningEntity = val("highest_warning_level");
    const warningLevel = warningEntity?.state || "none";

    // Nearest
    const nearestEntity = val("nearest_incident");
    const nearest = nearestEntity ? {
      distance: nearestEntity.state !== "unknown" && nearestEntity.state !== "unavailable"
        ? parseFloat(nearestEntity.state) : null,
      ...nearestEntity.attributes,
    } : null;

    // Feed status
    const feedEntity = val("feed_status");
    const feedStatus = feedEntity?.state || "unknown";

    // Total
    const total = parseInt(totalState.state, 10) || 0;

    // Build flat incident list from group sensor attributes
    const incidents = [];
    for (const [key, group] of Object.entries(groups)) {
      for (const inc of group.incidents) {
        incidents.push({ ...inc, group: key });
      }
    }
    incidents.sort((a, b) => (a.distance_km ?? 9999) - (b.distance_km ?? 9999));

    return { total, groups, warningLevel, nearest, feedStatus, incidents, prefix };
  }

  // ─── Header ──────────────────────────────────────────────────

  _renderHeader(data, warning) {
    const title = this._config.title || "VicEmergency";
    const countText = data.total === 0
      ? "No active incidents"
      : `${data.total} active incident${data.total !== 1 ? "s" : ""}`;

    return `
      <div class="ve-header">
        <div class="ve-header-top">
          <div class="ve-title-group">
            <span class="ve-title">${this._esc(title)}</span>
            <span class="ve-count">${countText}</span>
          </div>
          <div class="ve-warning-badge" style="--badge-colour: ${warning.colour}; --badge-bg: ${warning.bg}">
            <ha-icon icon="${warning.icon}"></ha-icon>
            <span>${warning.label}</span>
          </div>
        </div>
        ${data.nearest && data.nearest.distance !== null ? `
          <div class="ve-nearest">
            <ha-icon icon="mdi:map-marker-distance"></ha-icon>
            <span>Nearest: <strong>${data.nearest.distance} km ${data.nearest.bearing || ""}</strong></span>
            <span class="ve-nearest-detail">${this._esc(data.nearest.title || "")}</span>
          </div>
        ` : ""}
      </div>
    `;
  }

  // ─── Category chips ──────────────────────────────────────────

  _renderCategoryBar(data) {
    const chips = Object.entries(GROUP_META).map(([key, meta]) => {
      const g = data.groups[key];
      const active = g && g.count > 0;
      return `
        <div class="ve-chip ${active ? "ve-chip--active" : ""}" style="--chip-colour: ${meta.colour}">
          <ha-icon icon="${meta.icon}"></ha-icon>
          <span class="ve-chip-count">${g ? g.count : 0}</span>
          <span class="ve-chip-label">${meta.label}</span>
        </div>
      `;
    }).join("");

    return `<div class="ve-categories">${chips}</div>`;
  }

  // ─── Incident list ───────────────────────────────────────────

  _renderIncidentList(data) {
    if (data.incidents.length === 0) {
      return `<div class="ve-empty">
        <ha-icon icon="mdi:shield-check"></ha-icon>
        <span>No incidents in this watch zone</span>
      </div>`;
    }

    const max = this._config.max_incidents || 10;
    const shown = data.incidents.slice(0, max);
    const remaining = data.incidents.length - shown.length;

    const rows = shown.map((inc) => {
      const groupMeta = GROUP_META[inc.group] || {};
      const ft = FEEDTYPE_META[inc.feedtype] || FEEDTYPE_META.incident;
      const dist = inc.distance_km != null ? `${inc.distance_km} km` : "";

      return `
        <div class="ve-incident">
          <div class="ve-incident-dot" style="background: ${ft.dot}"></div>
          <div class="ve-incident-body">
            <div class="ve-incident-title">${this._esc(inc.title || inc.location || "Unknown")}</div>
            <div class="ve-incident-meta">
              <span class="ve-incident-cat" style="color: ${groupMeta.colour || "#666"}">${this._esc(inc.category || "")}</span>
              ${inc.status ? `<span class="ve-incident-status">${this._esc(inc.status)}</span>` : ""}
            </div>
          </div>
          <div class="ve-incident-dist">${dist}</div>
        </div>
      `;
    }).join("");

    const moreRow = remaining > 0
      ? `<div class="ve-more">+ ${remaining} more incident${remaining !== 1 ? "s" : ""}</div>`
      : "";

    return `<div class="ve-incidents">${rows}${moreRow}</div>`;
  }

  // ─── Footer ──────────────────────────────────────────────────

  _renderFooter(data) {
    const feedDot = data.feedStatus === "ok" ? "#4CAF50"
      : data.feedStatus === "degraded" ? "#FF9800"
      : "#F44336";

    const feedLabel = data.feedStatus === "ok" ? "Feed OK"
      : data.feedStatus === "degraded" ? "Feed degraded"
      : "Feed error";

    const mapLink = this._config.show_map_link
      ? `<a class="ve-footer-link" href="https://emergency.vic.gov.au" target="_blank" rel="noopener">
           <ha-icon icon="mdi:open-in-new"></ha-icon> VicEmergency
         </a>
         <a class="ve-footer-link" href="https://www.abc.net.au/listen/live/melbourne" target="_blank" rel="noopener">
           <ha-icon icon="mdi:radio"></ha-icon> ABC 774
         </a>`
      : "";

    return `
      <div class="ve-footer">
        <div class="ve-feed-status">
          <span class="ve-feed-dot" style="background: ${feedDot}"></span>
          <span>${feedLabel}</span>
        </div>
        <div class="ve-footer-links">
          ${mapLink}
        </div>
      </div>
    `;
  }

  // ─── Error state ─────────────────────────────────────────────

  _renderError(msg) {
    this.innerHTML = `
      <ha-card>
        <div style="padding: 16px; color: var(--error-color, #D50000);">
          <ha-icon icon="mdi:alert-circle"></ha-icon>
          <span style="margin-left: 8px;">${this._esc(msg)}</span>
        </div>
      </ha-card>
    `;
  }

  // ─── Helpers ─────────────────────────────────────────────────

  _esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  // ─── Styles ──────────────────────────────────────────────────

  _styles() {
    return `
      .ve-card {
        padding: 16px;
        font-family: var(--ha-card-header-font-family, inherit);
      }

      /* ── Header ── */
      .ve-header { margin-bottom: 16px; }

      .ve-header-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
      }

      .ve-title-group {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .ve-title {
        font-size: 1.1em;
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .ve-count {
        font-size: 0.85em;
        color: var(--secondary-text-color);
      }

      .ve-warning-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 600;
        color: var(--badge-colour);
        background: var(--badge-bg);
        border: 1px solid color-mix(in srgb, var(--badge-colour) 25%, transparent);
        white-space: nowrap;
        flex-shrink: 0;
      }

      .ve-warning-badge ha-icon {
        --mdc-icon-size: 16px;
        color: var(--badge-colour);
      }

      .ve-nearest {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 10px;
        padding: 8px 10px;
        border-radius: 8px;
        background: var(--card-background-color, var(--ha-card-background, #fff));
        border: 1px solid var(--divider-color, #e0e0e0);
        font-size: 0.85em;
        color: var(--primary-text-color);
      }

      .ve-nearest ha-icon {
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
        flex-shrink: 0;
      }

      .ve-nearest-detail {
        color: var(--secondary-text-color);
        margin-left: auto;
        text-align: right;
        font-size: 0.9em;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 45%;
      }

      /* ── Category chips ── */
      .ve-categories {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        margin-bottom: 16px;
      }

      .ve-chip {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 10px;
        border-radius: 10px;
        background: var(--card-background-color, var(--ha-card-background, #fff));
        border: 1px solid var(--divider-color, #e0e0e0);
        opacity: 0.45;
        transition: opacity 0.2s, border-color 0.2s;
      }

      .ve-chip--active {
        opacity: 1;
        border-color: color-mix(in srgb, var(--chip-colour) 40%, transparent);
        background: color-mix(in srgb, var(--chip-colour) 6%, var(--card-background-color, #fff));
      }

      .ve-chip ha-icon {
        --mdc-icon-size: 18px;
        color: var(--chip-colour);
        flex-shrink: 0;
      }

      .ve-chip-count {
        font-weight: 700;
        font-size: 1em;
        color: var(--primary-text-color);
      }

      .ve-chip-label {
        font-size: 0.7em;
        color: var(--secondary-text-color);
        display: none;
      }

      @media (min-width: 400px) {
        .ve-chip-label { display: inline; }
      }

      /* ── Empty state ── */
      .ve-empty {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 24px 16px;
        color: var(--secondary-text-color);
        font-size: 0.9em;
      }

      .ve-empty ha-icon {
        --mdc-icon-size: 24px;
        color: #4CAF50;
      }

      /* ── Incident list ── */
      .ve-incidents {
        margin-bottom: 12px;
      }

      .ve-incident {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 0;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }

      .ve-incident:last-child {
        border-bottom: none;
      }

      .ve-incident-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-top: 5px;
        flex-shrink: 0;
      }

      .ve-incident-body {
        flex: 1;
        min-width: 0;
      }

      .ve-incident-title {
        font-size: 0.9em;
        font-weight: 500;
        color: var(--primary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .ve-incident-meta {
        display: flex;
        gap: 8px;
        font-size: 0.78em;
        margin-top: 2px;
      }

      .ve-incident-cat {
        font-weight: 600;
      }

      .ve-incident-status {
        color: var(--secondary-text-color);
      }

      .ve-incident-dist {
        font-size: 0.82em;
        font-weight: 600;
        color: var(--secondary-text-color);
        white-space: nowrap;
        flex-shrink: 0;
        margin-top: 2px;
      }

      .ve-more {
        text-align: center;
        padding: 8px;
        font-size: 0.82em;
        color: var(--secondary-text-color);
      }

      /* ── Footer ── */
      .ve-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        padding-top: 8px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
        font-size: 0.78em;
        color: var(--secondary-text-color);
      }

      .ve-feed-status {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .ve-footer-links {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .ve-feed-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }

      .ve-footer-link {
        display: flex;
        align-items: center;
        gap: 4px;
        color: var(--secondary-text-color);
        text-decoration: none;
        transition: color 0.15s;
      }

      .ve-footer-link:hover {
        color: var(--primary-text-color);
      }

      .ve-footer-link ha-icon {
        --mdc-icon-size: 14px;
      }
    `;
  }
}

// ───────────────────────────────────────────────────────────────
// Visual card editor
// ───────────────────────────────────────────────────────────────

class VicEmergencyCardEditor extends HTMLElement {

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) this._render();
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  _render() {
    if (!this._hass) return;
    this._rendered = true;

    // Find all vicemergency total_incidents sensors
    const entities = Object.keys(this._hass.states)
      .filter(e => e.startsWith("sensor.vicemergency_") && e.endsWith("_total_incidents"))
      .sort();

    const options = entities.map(e => {
      const friendly = this._hass.states[e]?.attributes?.friendly_name || e;
      return `<option value="${e}" ${e === this._config.entity ? "selected" : ""}>${friendly} (${e})</option>`;
    }).join("");

    const entitySelector = entities.length > 0
      ? `<select id="entity">${options}</select>`
      : `<input id="entity" value="${this._config.entity || ""}"
               placeholder="sensor.vicemergency_home_total_incidents">`;

    const hint = entities.length === 0
      ? `<div style="font-size:0.8em;color:var(--error-color,#D50000);margin-top:4px;">
           No VicEmergency zones found. Add the integration first via Settings → Devices & Services.
         </div>`
      : "";

    this.innerHTML = `
      <style>
        .editor-row { margin-bottom: 12px; }
        .editor-row label {
          display: block; font-size: 0.85em; margin-bottom: 4px;
          color: var(--secondary-text-color);
        }
        .editor-row input, .editor-row select {
          width: 100%; padding: 8px;
          border: 1px solid var(--divider-color, #ccc);
          border-radius: 6px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
          font-size: 0.9em; box-sizing: border-box;
        }
        .editor-row-check {
          display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
        }
        .editor-row-check label { margin: 0; font-size: 0.9em; }
      </style>

      <div class="editor-row">
        <label>Monitoring Zone *</label>
        ${entitySelector}
        ${hint}
      </div>
      <div class="editor-row">
        <label>Title</label>
        <input id="title" value="${this._config.title || "VicEmergency"}">
      </div>
      <div class="editor-row">
        <label>Max incidents shown</label>
        <input id="max_incidents" type="number" min="1" max="50"
               value="${this._config.max_incidents || 10}">
      </div>
      <div class="editor-row-check">
        <input type="checkbox" id="compact" ${this._config.compact ? "checked" : ""}>
        <label for="compact">Compact mode (hide incident list)</label>
      </div>
      <div class="editor-row-check">
        <input type="checkbox" id="show_map_link" ${this._config.show_map_link !== false ? "checked" : ""}>
        <label for="show_map_link">Show VicEmergency link</label>
      </div>
    `;

    const fire = () => {
      this.dispatchEvent(new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }));
    };

    this.querySelector("#entity").addEventListener(entities.length > 0 ? "change" : "input", (e) => {
      this._config.entity = e.target.value; fire();
    });

    // Auto-select first entity if none configured
    if (!this._config.entity && entities.length > 0) {
      this._config.entity = entities[0];
      fire();
    }

    this.querySelector("#title").addEventListener("input", (e) => {
      this._config.title = e.target.value; fire();
    });
    this.querySelector("#max_incidents").addEventListener("input", (e) => {
      this._config.max_incidents = parseInt(e.target.value, 10) || 10; fire();
    });
    this.querySelector("#compact").addEventListener("change", (e) => {
      this._config.compact = e.target.checked; fire();
    });
    this.querySelector("#show_map_link").addEventListener("change", (e) => {
      this._config.show_map_link = e.target.checked; fire();
    });
  }
}

// ───────────────────────────────────────────────────────────────
// Registration
// ───────────────────────────────────────────────────────────────

customElements.define("vicemergency-card", VicEmergencyCard);
customElements.define("vicemergency-card-editor", VicEmergencyCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vicemergency-card",
  name: "VicEmergency Card",
  preview: true,
  description: "Victorian emergency incidents with warning levels, category breakdown, and incident list.",
});
