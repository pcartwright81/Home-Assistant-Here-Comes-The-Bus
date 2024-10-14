"""Define a device tracker."""

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import Const
from .coordinator import HCBDataCoordinator
from .student_data import StudentData


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up bus sensors."""
    if bool(config_entry.data.get("AddDeviceTracker", True)) is not True:
        return

    coordinator = config_entry.runtime_data
    async_add_entities(HCBTracker(coordinator, key) for key in coordinator.data)


class HCBTracker(CoordinatorEntity[StudentData], TrackerEntity):
    """Defines a single bus sensor."""

    def __init__(self, coordinator: HCBDataCoordinator, key: str) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        data = coordinator.data[key]
        self.name = data.first_name + " Bus"
        self.unique_id = data.first_name.lower() + "_bus"
        self._student_id = data.student_id
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

    def _update_location(self, data: StudentData):
        self._attr_latitude = data.latitude
        self._attr_longitude = data.longitude
        self._attr_address = data.address
        self._attr_extra_state_attributes = {
            Const.ATTR_BUS_NAME: data.bus_name,
            Const.ATTR_SPEED: data.speed,
            Const.ATTR_MESSAGE_CODE: data.message_code,
            Const.ATTR_DISPLAY_ON_MAP: data.display_on_map,
            Const.ATTR_IGNITION: data.ignition,
            Const.ATTR_LOG_TIME: data.log_time,
            Const.ATTR_HEADING: data.heading,
            Const.ATTR_AM_SCHOOL_ARRIVAL_TIME: data.am_school_arrival_time,
            Const.ATTR_PM_SCHOOL_ARRIVAL_TIME: data.pm_school_arrival_time,
            Const.ATTR_AM_STOP_ARRIVAL_TIME: data.am_stop_arrival_time,
            Const.ATTR_PM_STOP_ARRIVAL_TIME: data.pm_stop_arrival_time,
        }
