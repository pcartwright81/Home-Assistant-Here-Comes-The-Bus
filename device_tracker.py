"""Define a device tracker."""

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import Const
from .coordinator import HCBDataCoordinator


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up bus sensors."""
    coordinator = config_entry.runtime_data
    async_add_entities(HCBTracker(coordinator, key) for key in coordinator.data)


class HCBTracker(CoordinatorEntity, TrackerEntity):
    """Defines a single bus sensor."""

    def __init__(self, coordinator: HCBDataCoordinator, key: str) -> None:
        data = coordinator.data[key]
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self.name = data.student.first_name + " Bus"
        self.unique_id = data.student.first_name.lower() + "_bus"
        self._student_id = data.student.entity_id
        self._update_location(data)
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(Const.DOMAIN, self._student_id)},
            manufacturer=Const.DEFAULT_NAME,
            name=Const.DEFAULT_NAME,
        )

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        data = self.coordinator.data[self._student_id]
        self._update_location(data)
        self.async_write_ha_state()

    def _update_location(self, data):
        vehicle_location = data.vehiclelocation
        if vehicle_location is not None: #keep it this way because we have more attributes in stops
            self._attr_latitude = float(vehicle_location.latitude)
            self._attr_longitude = float(vehicle_location.longitude)
            self._attr_address = vehicle_location.addess
            self._attr_extra_state_attributes = {
                Const.ATTR_BUS_NAME: vehicle_location.name,
                Const.ATTR_SPEED: vehicle_location.speed,
                Const.ATTR_MESSAGE_CODE: vehicle_location.message_code,
                Const.ATTR_DISPLAY_ON_MAP: vehicle_location.display_on_map,
                Const.ATTR_IGNITION: vehicle_location.ignition,
                Const.ATTR_LOG_TIME: vehicle_location.log_time,
            }
