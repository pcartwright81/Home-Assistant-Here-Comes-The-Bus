"""Define sensors."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from attr import dataclass
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    CONF_ADD_SENSORS,
)
from .coordinator import HCBDataCoordinator
from .data import HCBConfigEntry, StudentData
from .entity import HCBEntity

type StateType = str | datetime | float | None
DEFAULT_ICON = "def_icon"


@dataclass(frozen=True, kw_only=True)
class HCBSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """A class that describes ThinQ sensor entities."""

    unit_fn: Callable[[Any], str] | None = None
    value_fn: Callable[[StudentData], float | str | datetime | None] | None = None


ENTITY_DESCRIPTIONS: tuple[HCBSensorEntityDescription, ...] = (
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
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: HCBConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bus sensors."""
    if bool(entry.data.get(CONF_ADD_SENSORS, True)) is not True:
        return

    async_add_entities(
        HCBSensor(entry.runtime_data.coordinator, entity_description, student)
        for entity_description in ENTITY_DESCRIPTIONS
        for student in entry.runtime_data.coordinator.data.values()
    )


class HCBSensor(HCBEntity, SensorEntity):
    """Defines a single bus sensor."""

    entity_description: HCBSensorEntityDescription

    def __init__(
        self,
        coordinator: HCBDataCoordinator,
        description: HCBSensorEntityDescription,
        student: StudentData,
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, student, description)

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.student)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        self.student = self.coordinator.data[self.student.student_id]
        self.async_write_ha_state()
