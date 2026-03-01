"""Binary sensor platform for the VicEmergency integration.

One binary sensor per category group per zone.
ON = at least one active incident of that type in the zone.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, GROUP_FRIENDLY_NAMES, GROUP_ICONS, MANUFACTURER, SUMMARY_GROUPS
from .coordinator import VicEmergencyCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    entry_data = hass.data[DOMAIN]["entries"][entry.entry_id]
    coordinator: VicEmergencyCoordinator = entry_data["coordinator"]
    zone_name: str = entry_data["zone_config"].name

    async_add_entities(
        [VicEmergencyGroupBinarySensor(coordinator, entry, zone_name, group) for group in SUMMARY_GROUPS],
        update_before_add=True,
    )


class VicEmergencyGroupBinarySensor(CoordinatorEntity[VicEmergencyCoordinator], BinarySensorEntity):
    """Binary sensor — ON when any incident of a category group is active."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator, entry, zone_name, group):
        super().__init__(coordinator)
        self._entry = entry
        self._zone_name = zone_name
        self._group = group
        friendly = GROUP_FRIENDLY_NAMES.get(group, group)
        self._attr_unique_id = f"{entry.entry_id}_{group}_active"
        self._attr_name = f"{friendly} Active"

    @property
    def is_on(self) -> bool:
        incidents = self.coordinator.get_zone_incidents(self._entry.entry_id)
        return any(i.category_group == self._group for i in incidents)

    @property
    def icon(self) -> str:
        return GROUP_ICONS.get(self._group, "mdi:alert")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"VicEmergency {self._zone_name}",
            manufacturer=MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://emergency.vic.gov.au",
        )
