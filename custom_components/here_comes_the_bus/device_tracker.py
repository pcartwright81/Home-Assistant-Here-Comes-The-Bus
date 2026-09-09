"""Define a device tracker."""

from collections.abc import Callable

from attr import dataclass
from homeassistant.components.device_tracker import (
    TrackerEntity,  # type: ignore i am pretty sure it is but ?
    TrackerEntityDescription,  # type: ignore i am pretty sure it is but ?
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
        key="location",
        latitude_fn=lambda x: x.latitude,
        longitude_fn=lambda x: x.longitude,
        address_fn=lambda x: x.address,
    ),
]


async def async_setup_entry(
    _: HomeAssistant,
    entry: HCBConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bus sensors."""
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

    @property
    def location_name(self) -> str | None:
        """Return a location name for the current location of the device."""
        return self.entity_description.address_fn(self.student)

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        return self.entity_description.latitude_fn(self.student)

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        return self.entity_description.longitude_fn(self.student)

    @property
    def location_accuracy(self) -> int:
        """Return the gps accuracy of the device."""
        return 100

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Record GPS freshness alongside positions for future ETA reconstruction."""
        return {
            "eta_speed": self.student.speed,
            "eta_log_time": self.student.log_time.isoformat()
            if self.student.log_time
            else None,
            "eta_gps_valid": self.student.display_on_map is True
            and self.student.latent is False,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated self.student from the coordinator."""
        if self.student.student_id in self.coordinator.data:
            self.student = self.coordinator.data[self.student.student_id]
            self.async_write_ha_state()
