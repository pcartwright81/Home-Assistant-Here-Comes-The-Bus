"""Define sensors."""

from collections.abc import Callable
from datetime import datetime, time
from typing import Any

from attr import dataclass
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import (
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ADDRESS,
    ATTR_AM_ARRIVAL_TIME,
    ATTR_BUS_NAME,
    ATTR_HEADING,
    ATTR_LOG_TIME,
    ATTR_MESSAGE_CODE,
    ATTR_PM_ARRIVAL_TIME,
    ATTR_SPEED,
    LOGGER,
)
from .coordinator import HCBDataCoordinator
from .data import HCBConfigEntry, StudentData
from .entity import HCBEntity


@dataclass(frozen=True, kw_only=True)
class HCBSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """A class that describes sensor entities."""

    value_fn: Callable[[StudentData], float | str | datetime | time | None]


def format_message_code(message_code: int | None) -> str:
    """Format the message code to a string value."""
    if message_code == 0:
        return "In Service"
    if message_code is None or message_code == 2:  # noqa: PLR2004 fix this later
        return "Out Of Service"
    LOGGER.error("Message code was %s", message_code)
    return str(message_code)


def _format_time(input_time: time | None) -> str:
    if input_time is None:
        return "00:00"
    return input_time.strftime("%H:%M")


ENTITY_DESCRIPTIONS: tuple[HCBSensorEntityDescription, ...] = (
    HCBSensorEntityDescription(
        key=ATTR_BUS_NAME,
        name="Number",
        value_fn=lambda x: x.bus_name,
    ),
    HCBSensorEntityDescription(
        key=ATTR_SPEED,
        name="Speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda x: x.speed,
    ),
    HCBSensorEntityDescription(
        key=ATTR_MESSAGE_CODE,
        name="Message",
        value_fn=lambda x: format_message_code(x.message_code),
    ),
    HCBSensorEntityDescription(
        key=ATTR_ADDRESS,
        name="Address",
        value_fn=lambda x: x.address,
    ),
    HCBSensorEntityDescription(
        key=ATTR_HEADING,
        name="Heading",
        value_fn=lambda x: x.heading,
    ),
    HCBSensorEntityDescription(
        key=ATTR_LOG_TIME,
        name="Log time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda x: x.log_time,
    ),
    HCBSensorEntityDescription(
        key=ATTR_AM_ARRIVAL_TIME,
        name="AM arrival time",
        value_fn=lambda x: _format_time(x.am_arrival_time),
    ),
    HCBSensorEntityDescription(
        key=ATTR_PM_ARRIVAL_TIME,
        name="PM arrival time",
        value_fn=lambda x: _format_time(x.pm_arrival_time),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: HCBConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bus sensors."""
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
    def native_value(self) -> Any:
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
