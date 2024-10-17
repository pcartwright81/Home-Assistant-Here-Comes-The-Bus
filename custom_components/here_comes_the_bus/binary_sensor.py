"""Support for Here comes the bus binary sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import get_device_info
from .const import ATTR_DISPLAY_ON_MAP, ATTR_IGNITION, BUS, CONF_ADD_SENSORS
from .coordinator import HCBDataCoordinator
from .student_data import StudentData

type StateType = str | int | float | None
DEFAULT_ICON = "def_icon"


@dataclass
class HCBBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes Here comes the bus binary sensor entities."""

    icon_on: str | None = None
    value_fn: Callable[[Any], bool | str] | None = None


sensor_descs: tuple[HCBBinarySensorEntityDescription, ...] = (
    HCBBinarySensorEntityDescription(
        key=ATTR_IGNITION,
        name="Ignition on",
        value_fn=lambda x: x.ignition,
        icon="mdi:engine-off",
        icon_on="mdi:engine",
    ),
    HCBBinarySensorEntityDescription(
        key=ATTR_DISPLAY_ON_MAP,
        name="Display on map",
        value_fn=lambda x: x.display_on_map,
        icon="mdi:map-marker-alert",
        icon_on="mdi:map-marker-check",
    ),
)


async def async_setup_entry(
    _: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up bus binary sensors."""
    if bool(config_entry.data.get(CONF_ADD_SENSORS, True)) is not True:
        return

    coordinator: HCBDataCoordinator = config_entry.runtime_data
    sensors = [
        HCBBinarySensor(coordinator, student, sensor_desc)
        for sensor_desc in sensor_descs
        for student in coordinator.data.values()
    ]
    async_add_entities(sensors)


class HCBBinarySensor(CoordinatorEntity[StudentData], BinarySensorEntity):
    """Defines a single bus sensor."""

    entity_description: HCBBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HCBDataCoordinator,
        student: StudentData,
        description: HCBBinarySensorEntityDescription,
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._student = student
        self.entity_description = description
        self._is_on = None

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
    def is_on(self):
        """Return true if the binary sensor is on."""
        self._is_on = self.entity_description.value_fn(self._student)
        return self._is_on

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        if self.entity_description.icon_on and self._is_on:
            return self.entity_description.icon_on
        return super().icon

    def _get_on_state(self):
        """Return true if the binary sensor is on."""
        ret_val = self._get_sensor_state()
        if ret_val is None:
            return False
        return ret_val

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        self._student = self.coordinator.data[self._student_id]
        self.async_write_ha_state()
