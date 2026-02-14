"""Sensor platform for the CFA Fire Forecast integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_FORECAST_DAYS,
    DEFAULT_FORECAST_DAYS,
    DISTRICTS,
    DOMAIN,
    MANUFACTURER,
    RATING_COLOURS,
    RATING_ICONS,
)
from .coordinator import CfaFireForecastCoordinator

_LOGGER = logging.getLogger(__name__)

# Day labels used in entity naming / unique IDs
DAY_LABELS = ["today", "tomorrow", "day_3", "day_4"]
DAY_FRIENDLY = ["Today", "Tomorrow", "Day 3", "Day 4"]

_ENTRIES_KEY = "entries"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CFA Fire Forecast sensors from a config entry."""
    entry_data = hass.data[DOMAIN][_ENTRIES_KEY][entry.entry_id]
    coordinator: CfaFireForecastCoordinator = entry_data["coordinator"]
    district_slug: str = entry_data["district_slug"]

    forecast_days: int = entry.options.get(CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS)

    entities: list[SensorEntity] = []
    valid_unique_ids: set[str] = set()

    # Create a sensor for each forecast day
    for day_index in range(forecast_days):
        rating_sensor = CfaFireDangerRatingSensor(
            coordinator, entry, district_slug, day_index
        )
        tfb_sensor = CfaTotalFireBanSensor(
            coordinator, entry, district_slug, day_index
        )
        entities.append(rating_sensor)
        entities.append(tfb_sensor)
        valid_unique_ids.add(rating_sensor.unique_id)
        valid_unique_ids.add(tfb_sensor.unique_id)

    # Overall "max severity" sensor for automations
    max_sensor = CfaMaxSeveritySensor(coordinator, entry, district_slug)
    entities.append(max_sensor)
    valid_unique_ids.add(max_sensor.unique_id)

    # Diagnostic sensor for feed health
    status_sensor = CfaFeedStatusSensor(coordinator, entry, district_slug)
    entities.append(status_sensor)
    valid_unique_ids.add(status_sensor.unique_id)

    # --- Stale entity cleanup ---
    # Remove entities that no longer belong to this config entry
    # (e.g. if sensor types changed between versions).
    ent_reg = async_get_entity_registry(hass)
    for entity_entry in list(ent_reg.entities.values()):
        if (
            entity_entry.platform == DOMAIN
            and entity_entry.config_entry_id == entry.entry_id
            and entity_entry.unique_id not in valid_unique_ids
        ):
            _LOGGER.info(
                "Removing stale CFA entity: %s (uid=%s)",
                entity_entry.entity_id,
                entity_entry.unique_id,
            )
            ent_reg.async_remove(entity_entry.entity_id)

    async_add_entities(entities, update_before_add=True)


class CfaBaseSensor(CoordinatorEntity[CfaFireForecastCoordinator], SensorEntity):
    """Base class for CFA sensors."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: CfaFireForecastCoordinator,
        entry: ConfigEntry,
        district_slug: str,
    ) -> None:
        """Initialise the base sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._district_slug = district_slug
        self._district_name = DISTRICTS.get(district_slug, district_slug)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for grouping entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._district_slug)},
            name=f"CFA {self._district_name} Fire District",
            manufacturer=MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=(
                "https://www.cfa.vic.gov.au/warnings-restrictions/"
                f"total-fire-bans-and-ratings/{self._district_slug}-fire-district"
            ),
        )

    def _get_district_data(self) -> dict[str, Any] | None:
        """Retrieve this district's data block from the shared coordinator."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._district_slug)

    def _get_forecast(self, index: int) -> dict[str, Any] | None:
        """Safely retrieve a forecast day from coordinator data."""
        district_data = self._get_district_data()
        if district_data is None:
            return None
        forecasts = district_data.get("forecasts", [])
        if index < len(forecasts):
            return forecasts[index]
        return None


class CfaFireDangerRatingSensor(CfaBaseSensor):
    """Sensor showing the fire danger rating for a specific forecast day."""

    def __init__(
        self,
        coordinator: CfaFireForecastCoordinator,
        entry: ConfigEntry,
        district_slug: str,
        day_index: int,
    ) -> None:
        """Initialise the fire danger rating sensor."""
        super().__init__(coordinator, entry, district_slug)
        self._day_index = day_index
        self._attr_unique_id = (
            f"cfa_{self._district_slug}_rating_{DAY_LABELS[day_index]}"
        )
        self._attr_name = f"Fire Danger Rating {DAY_FRIENDLY[day_index]}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the fire danger rating string."""
        forecast = self._get_forecast(self._day_index)
        if forecast is None:
            return None
        return forecast.get("rating", "UNKNOWN")

    @property
    def icon(self) -> str:
        """Return an icon based on the current rating level."""
        rating = str(self.native_value or "").upper()
        return RATING_ICONS.get(rating, "mdi:fire-alert")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        forecast = self._get_forecast(self._day_index)
        if forecast is None:
            return {}

        rating = forecast.get("rating", "UNKNOWN")
        district_data = self._get_district_data()
        attrs: dict[str, Any] = {
            "date": forecast.get("date_label"),
            "severity": forecast.get("severity", 0),
            "colour": RATING_COLOURS.get(rating, "#808080"),
            "total_fire_ban": forecast.get("total_fire_ban", False),
        }
        if forecast.get("issued_at"):
            attrs["forecast_issued_at"] = forecast["issued_at"]
        if district_data and district_data.get("pub_date"):
            attrs["feed_published"] = district_data["pub_date"]
        return attrs


class CfaTotalFireBanSensor(CfaBaseSensor):
    """Binary-style sensor showing Total Fire Ban status for a forecast day."""

    def __init__(
        self,
        coordinator: CfaFireForecastCoordinator,
        entry: ConfigEntry,
        district_slug: str,
        day_index: int,
    ) -> None:
        """Initialise the Total Fire Ban sensor."""
        super().__init__(coordinator, entry, district_slug)
        self._day_index = day_index
        self._attr_unique_id = (
            f"cfa_{self._district_slug}_tfb_{DAY_LABELS[day_index]}"
        )
        self._attr_name = f"Total Fire Ban {DAY_FRIENDLY[day_index]}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return 'Yes' or 'No' for Total Fire Ban status."""
        forecast = self._get_forecast(self._day_index)
        if forecast is None:
            return None
        return "Yes" if forecast.get("total_fire_ban", False) else "No"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        forecast = self._get_forecast(self._day_index)
        if forecast is None:
            return {}
        return {
            "date": forecast.get("date_label"),
            "fire_danger_rating": forecast.get("rating", "UNKNOWN"),
        }

    @property
    def icon(self) -> str:
        """Return icon based on TFB status."""
        forecast = self._get_forecast(self._day_index)
        if forecast and forecast.get("total_fire_ban"):
            return "mdi:fire-alert"
        return "mdi:fire-off"


class CfaMaxSeveritySensor(CfaBaseSensor):
    """Sensor showing the maximum fire danger severity across all forecast days."""

    def __init__(
        self,
        coordinator: CfaFireForecastCoordinator,
        entry: ConfigEntry,
        district_slug: str,
    ) -> None:
        """Initialise the max severity sensor."""
        super().__init__(coordinator, entry, district_slug)
        self._attr_unique_id = f"cfa_{self._district_slug}_max_severity"
        self._attr_name = "Max Fire Danger Rating"
        self._attr_icon = "mdi:fire"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | None:
        """Return the highest fire danger rating across all forecast days."""
        district_data = self._get_district_data()
        if district_data is None:
            return None
        forecasts = district_data.get("forecasts", [])
        if not forecasts:
            return None
        max_forecast = max(forecasts, key=lambda f: f.get("severity", 0))
        return max_forecast.get("rating", "UNKNOWN")

    @property
    def icon(self) -> str:
        """Return an icon based on the max rating level."""
        rating = str(self.native_value or "").upper()
        return RATING_ICONS.get(rating, "mdi:fire")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        district_data = self._get_district_data()
        if district_data is None:
            return {}
        forecasts = district_data.get("forecasts", [])
        if not forecasts:
            return {}
        max_forecast = max(forecasts, key=lambda f: f.get("severity", 0))
        any_tfb = any(f.get("total_fire_ban", False) for f in forecasts)
        rating = max_forecast.get("rating", "UNKNOWN")
        return {
            "severity": max_forecast.get("severity", 0),
            "colour": RATING_COLOURS.get(rating, "#808080"),
            "any_total_fire_ban": any_tfb,
            "worst_day": max_forecast.get("date_label"),
            "forecast_days": len(forecasts),
            "feed_source": self.coordinator.last_source,
        }


class CfaFeedStatusSensor(CfaBaseSensor):
    """Diagnostic sensor showing the health of the CFA data feed.

    State: ok / degraded / failed
      - ok:       combined feed working normally
      - degraded: running on individual-feed fallback, or some districts failed
      - failed:   no data available (coordinator has no data for this district)

    Attributes expose feed strategy, failure counts, and error details so
    users can build automations like "notify me if CFA feed is degraded
    for more than 2 hours".
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: CfaFireForecastCoordinator,
        entry: ConfigEntry,
        district_slug: str,
    ) -> None:
        """Initialise the feed status sensor."""
        super().__init__(coordinator, entry, district_slug)
        self._attr_unique_id = f"cfa_{self._district_slug}_feed_status"
        self._attr_name = "Feed Status"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return the feed health status."""
        # No data at all for this district
        district_data = self._get_district_data()
        if district_data is None or not district_data.get("forecasts"):
            return "failed"

        # Check if this specific district was in the failed list
        if self._district_slug in self.coordinator.failed_districts:
            return "failed"

        # Running on fallback or some districts had issues
        if (
            self.coordinator.fallback_active
            or self.coordinator.last_source == "individual"
            or self.coordinator.failed_districts
        ):
            return "degraded"

        return "ok"

    @property
    def icon(self) -> str:
        """Return icon reflecting feed health."""
        state = self.native_value
        if state == "ok":
            return "mdi:rss"
        if state == "degraded":
            return "mdi:alert-circle-outline"
        return "mdi:alert-circle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed feed diagnostics."""
        attrs: dict[str, Any] = {
            "feed_source": self.coordinator.last_source,
            "combined_failures": self.coordinator.combined_fail_count,
            "fallback_active": self.coordinator.fallback_active,
        }
        if self.coordinator.failed_districts:
            attrs["failed_districts"] = self.coordinator.failed_districts
        if self.coordinator.last_error:
            attrs["last_error"] = self.coordinator.last_error
        # last_update_success_time was added in HA 2023.x
        update_time = getattr(
            self.coordinator, "last_update_success_time", None
        )
        if update_time is not None:
            attrs["last_successful_update"] = update_time.isoformat()
        return attrs
