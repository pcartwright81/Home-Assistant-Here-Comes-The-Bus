"""Define a device tracker."""

from propcache import cached_property

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_device_info
from .const import (
    ATTR_AM_ARRIVAL_TIME,
    ATTR_BUS_NAME,
    ATTR_DISPLAY_ON_MAP,
    ATTR_HEADING,
    ATTR_IGNITION,
    ATTR_LOG_TIME,
    ATTR_MESSAGE_CODE,
    ATTR_PM_ARRIVAL_TIME,
    ATTR_SPEED,
    BUS,
    CONF_ADD_DEVICE_TRACKER,
)
from .coordinator import HCBDataCoordinator
from .student_data import StudentData


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up bus sensors."""
    if bool(config_entry.data.get(CONF_ADD_DEVICE_TRACKER, True)) is not True:
        return

    coordinator: HCBDataCoordinator = config_entry.runtime_data

    sensors = [
        HCBTracker(coordinator, student) for student in coordinator.data.values()
    ]
    async_add_entities(sensors)


class HCBTracker(CoordinatorEntity[StudentData], TrackerEntity):
    """Defines a single bus sensor."""

    def __init__(self, coordinator: HCBDataCoordinator, student: StudentData) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._student = student
        self.icon = "mdi:bus"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for this sensor."""
        return get_device_info(self._student)

    @property
    def name(self) -> str | None:
        """Return the name of this device."""
        return f"{self._student.first_name} {BUS}"

    @property
    def unique_id(self) -> str | None:
        """Return a unique identifier for this sensor."""
        return f"{self._student.first_name}_{BUS}"

    @cached_property
    def location_name(self) -> str | None:
        """Return a location name for the current location of the device."""
        return self._student.address

    @cached_property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self._student.latitude

    @cached_property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self._student.longitude

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            ATTR_BUS_NAME: self._student.bus_name,
            ATTR_SPEED: self._student.speed,
            ATTR_MESSAGE_CODE: self._student.message_code,
            ATTR_DISPLAY_ON_MAP: self._student.display_on_map,
            ATTR_IGNITION: self._student.ignition,
            ATTR_LOG_TIME: self._student.log_time,
            ATTR_HEADING: self._student.heading,
            ATTR_AM_ARRIVAL_TIME: self._student.am_arrival_time,
            ATTR_PM_ARRIVAL_TIME: self._student.pm_arrival_time,
        }

    @callback
    def _handle_coordinator_update(self):
        """Handle updated self._student from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        self._student = self.coordinator.data[self._student.student_id]
        self.async_write_ha_state()
