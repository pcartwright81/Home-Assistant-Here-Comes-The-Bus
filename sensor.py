"""Define sensors."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import HCBDataCoordinator
from .defaults import Defaults
from .student_data import StudentData

type StateType = str | int | float | None


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up bus sensors."""

    if bool(config_entry.data.get(Defaults.ADD_SENSORS, True)) is not True:
        return

    coordinator = config_entry.runtime_data
    sensors = []
    for student_id in coordinator.data:
        sensors.extend(
            [
                HCBSensor(coordinator, student_id, Defaults.ATTR_BUS_NAME),
                HCBSensor(coordinator, student_id, Defaults.ATTR_SPEED),
                HCBSensor(coordinator, student_id, Defaults.ATTR_MESSAGE_CODE),
                HCBBinarySensor(coordinator, student_id, Defaults.ATTR_DISPLAY_ON_MAP),
                HCBBinarySensor(coordinator, student_id, Defaults.ATTR_IGNITION),
                HCBSensor(coordinator, student_id, Defaults.ATTR_LOG_TIME),
                HCBSensor(coordinator, student_id, Defaults.ATTR_LATITUDE),
                HCBSensor(coordinator, student_id, Defaults.ATTR_LONGITUDE),
                HCBSensor(coordinator, student_id, Defaults.ATTR_ADDRESS),
                HCBSensor(coordinator, student_id, Defaults.ATTR_HEADING),
                HCBSensor(
                    coordinator, student_id, Defaults.ATTR_AM_SCHOOL_ARRIVAL_TIME
                ),
                HCBSensor(coordinator, student_id, Defaults.ATTR_PM_STOP_ARRIVAL_TIME),
            ]
        )

    async_add_entities(sensors)


def _get_state(_, data: StudentData, data_key: str):
    """Return the state for the data."""
    match data_key:
        case Defaults.ATTR_BUS_NAME:
            return data.bus_name
        case Defaults.ATTR_SPEED:
            return data.speed
        case Defaults.ATTR_MESSAGE_CODE:
            return data.message_code
        case Defaults.ATTR_DISPLAY_ON_MAP:
            return data.display_on_map
        case Defaults.ATTR_IGNITION:
            return data.ignition
        case Defaults.ATTR_ADDRESS:
            return data.address
        case Defaults.ATTR_LATITUDE:
            return data.latitude
        case Defaults.ATTR_LONGITUDE:
            return data.longitude
        case Defaults.ATTR_LOG_TIME:
            return data.log_time
        case Defaults.ATTR_HEADING:
            return data.heading
        case Defaults.ATTR_AM_SCHOOL_ARRIVAL_TIME:
            return data.am_school_arrival_time
        case Defaults.ATTR_PM_STOP_ARRIVAL_TIME:
            return data.pm_stop_arrival_time


class HCBSensor(CoordinatorEntity[StudentData], SensorEntity):
    """Defines a single bus sensor."""

    def __init__(
        self, coordinator: HCBDataCoordinator, student_id: str, attribute_name: str
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        data = coordinator.data[student_id]

        super().__init__(coordinator)
        self.name = f"{data.first_name} {Defaults.BUS} {attribute_name}"
        self.unique_id = f"{data.first_name}_{Defaults.BUS}_{attribute_name}".lower()
        self._student_id = data.student_id
        self.data_key = attribute_name
        self._sensor_data = None
        self._sensor_data = _get_state(self, data, self.data_key)
        self._attr_device_info = Defaults.get_device_info(self, data)

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return self._sensor_data

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        data = self.coordinator.data[self._student_id]
        self._sensor_data = _get_state(self, data, self.data_key)
        self.async_write_ha_state()


class HCBBinarySensor(CoordinatorEntity[StudentData], BinarySensorEntity):
    """Defines a single bus sensor."""

    def __init__(
        self, coordinator: HCBDataCoordinator, key: str, attribute_name: str
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        data = coordinator.data[key]
        self.name = f"{data.first_name} {Defaults.BUS} {attribute_name}"
        self.unique_id = f"{data.first_name}_{Defaults.BUS}_{attribute_name}".lower()
        self._student_id = data.student_id
        self.data_key = attribute_name
        self._sensor_data = _get_state(self, data, self.data_key)
        self._attr_device_info = Defaults.get_device_info(self, data)

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        return self._sensor_data

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        data = self.coordinator.data[self._student_id]
        self._sensor_data = _get_state(self, data, self.data_key)
        self.async_write_ha_state()
