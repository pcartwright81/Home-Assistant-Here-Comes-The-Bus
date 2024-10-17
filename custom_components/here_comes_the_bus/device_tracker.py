"""Define a device tracker."""

from collections.abc import Callable
from functools import cached_property
from typing import Any

from attr import dataclass
from homeassistant.components.device_tracker import (
    TrackerEntity,  # type: ignore i am pretty sure it is but ?
    TrackerEntityDescription,  # type: ignore i am pretty sure it is but ?
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    CONF_ADD_DEVICE_TRACKER,
)
from .coordinator import HCBDataCoordinator
from .data import HCBConfigEntry, StudentData
from .entity import HCBEntity


@dataclass(frozen=True, kw_only=True)
class HCBTrackerEntityDescription(TrackerEntityDescription, frozen_or_thawed=True):
    """Describes a here comes the bus tracker."""

    latitude_fn: Callable[[StudentData], float | None]
    longitude_fn: Callable[[StudentData], float | None]
    address_fn: Callable[[StudentData], str | None]


DEVICE_TRACKERS = [
    HCBTrackerEntityDescription(
        name="",
        key="device_location",
        latitude_fn=lambda x: x.latitude,
        longitude_fn=lambda x: x.longitude,
        address_fn=lambda x: x.address,
    ),
]

EXTRA_ATTRIBUTES: dict[str, Callable[[StudentData], Any]] = {
    ATTR_AM_ARRIVAL_TIME: lambda x: x.am_arrival_time,
    ATTR_BUS_NAME: lambda x: x.bus_name,
    ATTR_DISPLAY_ON_MAP: lambda x: x.display_on_map,
    ATTR_HEADING: lambda x: x.heading,
    ATTR_IGNITION: lambda x: x.ignition,
    ATTR_LOG_TIME: lambda x: x.log_time,
    ATTR_MESSAGE_CODE: lambda x: x.message_code,
    ATTR_SPEED: lambda x: x.speed,
    ATTR_PM_ARRIVAL_TIME: lambda x: x.pm_arrival_time,
}


async def async_setup_entry(
    _: HomeAssistant,
    entry: HCBConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bus sensors."""
    if bool(entry.data.get(CONF_ADD_DEVICE_TRACKER, True)) is not True:
        return

    async_add_entities(
        HCBTracker(entry.runtime_data.coordinator, student, tracker)
        for student in entry.runtime_data.coordinator.data.values()
        for tracker in DEVICE_TRACKERS
    )


class HCBTracker(HCBEntity, TrackerEntity):
    """Defines a single bus sensor."""

    entity_description: HCBTrackerEntityDescription

    def __init__(
        self,
        coordinator: HCBDataCoordinator,
        student: StudentData,
        description: HCBTrackerEntityDescription,
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, student, description)
        self.icon = "mdi:bus"

    @cached_property
    def location_name(self) -> str | None:
        """Return a location name for the current location of the device."""
        return self.entity_description.address_fn(self.student)

    @cached_property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self.entity_description.latitude_fn(self.student)

    @cached_property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self.entity_description.longitude_fn(self.student)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        extra_attributes = {}
        for key, value in EXTRA_ATTRIBUTES.items():
            extra_attributes[key] = value(self.student)
        return extra_attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated self.student from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        self.student = self.coordinator.data[self.student.student_id]
        self.async_write_ha_state()
