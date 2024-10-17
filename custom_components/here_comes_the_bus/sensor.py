"""Define sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_device_info
from .const import (
    ATTR_ADDRESS,
    ATTR_AM_ARRIVAL_TIME,
    ATTR_BUS_NAME,
    ATTR_HEADING,
    ATTR_LATITUDE,
    ATTR_LOG_TIME,
    ATTR_LONGITUDE,
    ATTR_MESSAGE_CODE,
    ATTR_PM_ARRIVAL_TIME,
    ATTR_SPEED,
    BUS,
    CONF_ADD_SENSORS,
)
from .coordinator import HCBDataCoordinator
from .student_data import StudentData

type StateType = str | int | float | None
DEFAULT_ICON = "def_icon"


@dataclass
class HCBSensorEntityDescription(SensorEntityDescription):
    """A class that describes ThinQ sensor entities."""

    unit_fn: Callable[[Any], str] | None = None
    value_fn: Callable[[Any], float | str] | None = None


sensor_descs: tuple[HCBSensorEntityDescription, ...] = (
    HCBSensorEntityDescription(
        key=ATTR_BUS_NAME,
        name="Number",
        value_fn=lambda x: x.bus_name,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_SPEED,
        name="Speed",
        value_fn=lambda x: x.speed,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_MESSAGE_CODE,
        name="Message code",
        value_fn=lambda x: x.message_code,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_LOG_TIME,
        name="Log time",
        value_fn=lambda x: x.log_time,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_LATITUDE,
        name="Latitude",
        value_fn=lambda x: x.latitude,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_LONGITUDE,
        name="Longitude",
        value_fn=lambda x: x.longitude,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_ADDRESS,
        name="Address",
        value_fn=lambda x: x.address,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_HEADING,
        name="Heading",
        value_fn=lambda x: x.heading,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_AM_ARRIVAL_TIME,
        name="AM arrival time",
        value_fn=lambda x: x.am_arrival_time,
        icon="mdi:bus",
    ),
    HCBSensorEntityDescription(
        key=ATTR_PM_ARRIVAL_TIME,
        name="PM arrival time",
        value_fn=lambda x: x.pm_arrival_time,
        icon="mdi:bus",
    ),
)


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up bus sensors."""

    if bool(config_entry.data.get(CONF_ADD_SENSORS, True)) is not True:
        return

    coordinator: HCBDataCoordinator = config_entry.runtime_data
    sensors = [
        HCBSensor(coordinator, student, sensor_desc)
        for sensor_desc in sensor_descs
        for student in coordinator.data.values()
    ]
    async_add_entities(sensors)


class HCBSensor(CoordinatorEntity[StudentData], SensorEntity):
    """Defines a single bus sensor."""

    entity_description: HCBSensorEntityDescription

    def __init__(
        self,
        coordinator: HCBDataCoordinator,
        student: StudentData,
        description: HCBSensorEntityDescription,
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._student = student
        self.entity_description = description
        self.icon = description.icon

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for this sensor."""
        return get_device_info(self._student)

    @property
    def name(self) -> str | None:
        """Return the name of this device."""
        return f"{self._student.first_name} {BUS} {self.entity_description.name}"

    @property
    def unique_id(self) -> str | None:
        """Return a unique identifier for this sensor."""
        return f"{self._student.first_name}_{BUS}_{self.entity_description.key}".lower()

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self._student)

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        self._student = self.coordinator.data[self._student.student_id]
        self.async_write_ha_state()
