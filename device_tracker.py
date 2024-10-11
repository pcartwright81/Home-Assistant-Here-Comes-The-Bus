"""Define a device tracker."""

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import DataUpdateEntity, HCBDataCoordinator

ATTR_BUS_NAME = "Bus Name"
ATTR_SPEED = "Speed"
ATTR_MESSAGE_CODE = "Message Code"
ATTR_DISPLAY_ON_MAP = "Display On Map"
ATTR_IGNITION = "Ignition On"
ATTR_LOG_TIME = "Last Seen"


async def async_setup_entry(_: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up bus sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        HCBTracker(coordinator, idx, ent) for idx, ent in enumerate(coordinator.data)
    )


class HCBTracker(CoordinatorEntity, TrackerEntity):
    """Defines a single bus sensor."""

    def __init__(
        self, coordinator: HCBDataCoordinator, idx: int, ent: DataUpdateEntity
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self.name = ent.student.first_name + " Bus"
        self.unique_id = ent.student.first_name.lower() + "_bus"
        self._attr_extra_state_attributes = {
            ATTR_BUS_NAME: None,
            ATTR_SPEED: None,
            ATTR_MESSAGE_CODE: None,
            ATTR_DISPLAY_ON_MAP: None,
            ATTR_IGNITION: None,
            ATTR_LOG_TIME: None,
        }
        self._update_atributes(ent)

    def _update_atributes(self, ent: DataUpdateEntity):
        if ent.vehiclelocation is not None:
            self._attr_latitude = ent.vehiclelocation.latitude
            self._attr_longitude = ent.vehiclelocation.longitude
            self._attr_extra_state_attributes = {
                ATTR_BUS_NAME: ent.vehiclelocation.name,
                ATTR_SPEED: ent.vehiclelocation.speed,
                ATTR_MESSAGE_CODE: ent.vehiclelocation.message_code,
                ATTR_DISPLAY_ON_MAP: ent.vehiclelocation.display_on_map,
                ATTR_IGNITION: ent.vehiclelocation.ignition,
                ATTR_LOG_TIME: ent.vehiclelocation.log_time,
            }

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        ent = self.coordinator.data[self.idx]
        self._update_atributes(ent)
        self.async_write_ha_state()
