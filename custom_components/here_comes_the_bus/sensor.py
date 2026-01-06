"""Define sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import (
    UnitOfSpeed,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HCBDataCoordinator
from .data import HCBConfigEntry, StudentData
from .entity import HCBEntity


@dataclass(frozen=True, kw_only=True)
class HCBSensorEntityDescription(SensorEntityDescription):
    """A class that describes sensor entities."""

    value_fn: Callable[[StudentData], float | str | datetime | time | None]


ENTITY_DESCRIPTIONS: tuple[HCBSensorEntityDescription, ...] = (
    HCBSensorEntityDescription(
        key="bus_name",
        name="Number",
        value_fn=lambda x: x.bus_name,
    ),
    HCBSensorEntityDescription(
        key="speed",
        name="Speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.MILES_PER_HOUR,
        value_fn=lambda x: x.speed,
    ),
    HCBSensorEntityDescription(
        key="address",
        name="Address",
        value_fn=lambda x: x.address,
    ),
    HCBSensorEntityDescription(
        key="heading",
        name="Heading",
        value_fn=lambda x: x.heading,
    ),
    HCBSensorEntityDescription(
        key="log_time",
        name="Log time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda x: x.log_time,
    ),
    HCBSensorEntityDescription(
        key="am_school_arrival_time",
        name="AM school arrival time",
        value_fn=lambda x: x.am_school_arrival_time,
    ),
    HCBSensorEntityDescription(
        key="am_stop_arrival_time",
        name="AM stop arrival time",
        value_fn=lambda x: x.am_stop_arrival_time,
    ),
    HCBSensorEntityDescription(
        key="mid_school_arrival_time",
        name="mid school arrival time",
        value_fn=lambda x: x.mid_school_arrival_time,
    ),
    HCBSensorEntityDescription(
        key="mid_stop_arrival_time",
        name="mid stop arrival time",
        value_fn=lambda x: x.mid_stop_arrival_time,
    ),
    HCBSensorEntityDescription(
        key="pm_school_arrival_time",
        name="PM school arrival time",
        value_fn=lambda x: x.pm_school_arrival_time,
    ),
    HCBSensorEntityDescription(
        key="pm_stop_arrival_time",
        name="PM stop arrival time",
        value_fn=lambda x: x.pm_stop_arrival_time,
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: HCBConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bus sensors."""
    async_add_entities(
        HCBSensor(entry.runtime_data.coordinator, entity_description, student)
        for entity_description in ENTITY_DESCRIPTIONS
        for student in entry.runtime_data.coordinator.data.values()
        if student.has_mid_stops
        or entity_description.key
        not in ("mid_school_arrival_time", "mid_stop_arrival_time")
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
        return self.entity_description.value_fn(self.student)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.student.student_id in self.coordinator.data:
            self.student = self.coordinator.data[self.student.student_id]
            self.async_write_ha_state()
