"""Define sensors."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

type StateType = str | int | float | None
from .const import Const
from .coordinator import HCBDataCoordinator
from .student_data import StudentData


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up bus sensors."""

    if bool(config_entry.data.get("AddSensors", True)) is not True:
        return

    coordinator = config_entry.runtime_data
    sensors = []
    for student_id in coordinator.data:
        sensors.extend(
            [
                HCBSensor(coordinator, student_id, Const.ATTR_BUS_NAME),
                HCBSensor(coordinator, student_id, Const.ATTR_SPEED),
                HCBSensor(coordinator, student_id, Const.ATTR_MESSAGE_CODE),
                HCBBinarySensor(coordinator, student_id, Const.ATTR_DISPLAY_ON_MAP),
                HCBBinarySensor(coordinator, student_id, Const.ATTR_IGNITION),
                HCBSensor(coordinator, student_id, Const.ATTR_LOG_TIME),
                HCBSensor(coordinator, student_id, Const.ATTR_LATITUDE),
                HCBSensor(coordinator, student_id, Const.ATTR_LONGITUDE),
                HCBSensor(coordinator, student_id, Const.ATTR_ADDRESS),
                HCBSensor(coordinator, student_id, Const.ATTR_HEADING),
                HCBSensor(coordinator, student_id, Const.ATTR_AM_SCHOOL_ARRIVAL_TIME),
                HCBSensor(coordinator, student_id, Const.ATTR_PM_STOP_ARRIVAL_TIME),
            ]
        )

    async_add_entities(sensors)


class DataUpdater:
    """Define a sensor entity/"""

    def get_state(self, data: StudentData, data_key: str):
        """Return the state for the data."""
        match data_key:
            case Const.ATTR_BUS_NAME:
                return data.bus_name
            case Const.ATTR_SPEED:
                return data.speed
            case Const.ATTR_MESSAGE_CODE:
                return data.message_code
            case Const.ATTR_DISPLAY_ON_MAP:
                return data.display_on_map
            case Const.ATTR_IGNITION:
                return data.ignition
            case Const.ATTR_ADDRESS:
                return data.address
            case Const.ATTR_LATITUDE:
                return data.latitude
            case Const.ATTR_LONGITUDE:
                return data.longitude
            case Const.ATTR_LOG_TIME:
                return data.log_time
            case Const.ATTR_HEADING:
                return data.heading
            case Const.ATTR_AM_SCHOOL_ARRIVAL_TIME:
                return data.am_school_arrival_time
            case Const.ATTR_PM_STOP_ARRIVAL_TIME:
                return data.pm_stop_arrival_time

class HCBSensor(CoordinatorEntity, SensorEntity):
    """Defines a single bus sensor."""

    def __init__(
        self, coordinator: HCBDataCoordinator, student_id: str, attribute_name: str
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        data = coordinator.data[student_id]

        super().__init__(coordinator)
        self.name = data.first_name + " Bus" + " " + attribute_name
        self.unique_id = (
            data.first_name.lower() + "_bus_" + attribute_name.lower().replace(" ", "_")
        )
        self._student_id = data.student_id
        self.data_key = attribute_name
        self._sensor_data = DataUpdater.get_state(self, data, self.data_key)
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(Const.DOMAIN, self._student_id)},
            manufacturer=Const.DEFAULT_NAME,
            name=Const.DEFAULT_NAME,
        )

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
        self._sensor_data = DataUpdater.get_state(self, data, self.data_key)
        self.async_write_ha_state()


class HCBBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Defines a single bus sensor."""

    def __init__(
        self, coordinator: HCBDataCoordinator, key: str, attribute_name: str
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        data = coordinator.data[key]

        self.name = data.first_name + " Bus" + " " + attribute_name
        self.unique_id = (
            data.first_name.lower() + "_bus_" + attribute_name.lower().replace(" ", "_")
        )
        self._student_id = data.student_id
        self.data_key = attribute_name
        self._sensor_data = DataUpdater.get_state(self, data, self.data_key)
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(Const.DOMAIN, self._student_id)},
            manufacturer=Const.DEFAULT_NAME,
            name=Const.DEFAULT_NAME,
        )

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
        self._sensor_data = DataUpdater.get_state(self, data, self.data_key)
        self.async_write_ha_state()
