"""Define sensors."""

from homeassistant.components.sensor import SensorEntity
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
    sensors = []
    for key in coordinator.data:
        sensors.extend(
            [
                HCBTracker(coordinator, key, Const.ATTR_BUS_NAME),
                HCBTracker(coordinator, key, Const.ATTR_SPEED),
                HCBTracker(coordinator, key, Const.ATTR_MESSAGE_CODE),
                HCBTracker(
                    coordinator, key, Const.ATTR_DISPLAY_ON_MAP
                ),  # todo should be binary
                HCBTracker(
                    coordinator, key, Const.ATTR_IGNITION
                ),  # todo should be binary
                HCBTracker(coordinator, key, Const.ATTR_LOG_TIME),  # todo change type
                HCBTracker(coordinator, key, Const.ATTR_LATITUDE),
                HCBTracker(coordinator, key, Const.ATTR_LONGITUDE),
                HCBTracker(coordinator, key, Const.ATTR_ADDRESS),
            ]
        )

    async_add_entities(sensors)


class HCBTracker(CoordinatorEntity, SensorEntity):
    """Defines a single bus sensor."""

    def __init__(
        self, coordinator: HCBDataCoordinator, key: str, attribute_name: str
    ) -> None:
        data = coordinator.data[key]
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self.name = data.student.first_name + " Bus" + " " + attribute_name
        self.unique_id = (
            data.student.first_name.lower()
            + "_bus_"
            + attribute_name.lower().replace(" ", "_")
        )
        self._student_id = data.student.entity_id
        self.data_key = attribute_name
        self._update_data(data)
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
        self._update_data(data)
        self.async_write_ha_state()

    def _update_data(self, data):
        vehicle_location = data.vehiclelocation
        if (
            vehicle_location is not None
        ):  # keep it this way because we have more attributes in stops
            match self.data_key:
                case Const.ATTR_BUS_NAME:
                    self.state = vehicle_location.name
                case Const.ATTR_SPEED:
                    self.state = vehicle_location.speed
                case Const.ATTR_MESSAGE_CODE:
                    self.state = vehicle_location.message_code
                case Const.ATTR_DISPLAY_ON_MAP:
                    self.state = vehicle_location.display_on_map
                case Const.ATTR_IGNITION:
                    self.state = vehicle_location.ignition
                case Const.ATTR_ADDRESS:
                    self.state = vehicle_location.addess
                case Const.ATTR_LATITUDE:
                    self.state = vehicle_location.latitude
                case Const.ATTR_LONGITUDE:
                    self.state = vehicle_location.longitude
