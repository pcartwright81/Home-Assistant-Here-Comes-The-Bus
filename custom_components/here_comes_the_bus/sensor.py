"""Define sensors."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import (
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ETA_ENTITY_KEYS
from .coordinator import HCBDataCoordinator
from .data import HCBConfigEntry, StudentData
from .entity import HCBEntity
from .eta import MIN_TRIPS, Estimate

ETA_DETAILS = {
    "recorder_disabled": (
        "Arrival estimates are paused because Home Assistant Recorder is not enabled."
    ),
    "no_fresh_position": "Waiting for a fresh bus location.",
    "no_destination": "No stop is available for the current service period.",
    "outside_service_window": "Waiting for the next service period.",
    "gps_hidden": "Bus location is not being shared.",
    "gps_invalid": "Waiting for a valid bus location.",
    "gps_stale": "Waiting for a fresh bus location.",
    "gps_out_of_order": "Received an older bus location; waiting for an update.",
    "insufficient_movement": "Waiting for more bus movement to match the route.",
    "ambiguous_route": "Bus location matches multiple parts of past routes.",
    "prediction_expired": "Previous estimate has expired; waiting for a new estimate.",
    "projected": "Projecting from the last route match; announcements paused.",
    "passed": "Bus passed the stop's final approach; arrival is not confirmed.",
}


def estimated_arrival_details(student: StudentData) -> str:
    """Describe the existing calculation result without doing extra estimation."""
    result = student.eta_estimate
    if result is None:
        return ETA_DETAILS["no_fresh_position"]
    if result.reason == "completed":
        return (
            "Arrival reported by Here Comes The Bus."
            if result.source == "reported_arrival"
            else "Stop visit inferred from bus location; arrival is not confirmed."
        )
    if result.reason == "insufficient_history":
        return (
            f"Learning route: needs at least {MIN_TRIPS} completed trips "
            f"({result.available_trips} available)."
        )
    if result.reason == "insufficient_matches":
        return (
            f"Matching past trips: {result.matching_trips} of "
            f"{result.available_trips}; at least {MIN_TRIPS} needed for an estimate."
        )
    if result.reason == "matched":
        return (
            "Past trips give conflicting arrival estimates; announcements paused."
            if result.confidence == "divergent"
            else f"Tracking arrival using {result.matching_trips} matching trips."
        )
    return ETA_DETAILS.get(result.reason, "Waiting for an arrival estimate.")


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
    HCBSensorEntityDescription(
        key="stop_eta",
        name="Estimated time until arrival",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda x: x.stop_eta,
    ),
    HCBSensorEntityDescription(
        key="eta_status",
        name="Estimated arrival status",
        value_fn=lambda x: x.eta_status,
    ),
    HCBSensorEntityDescription(
        key="eta_details",
        name="Estimated arrival details",
        value_fn=estimated_arrival_details,
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
        if entry.runtime_data.coordinator.eta_enabled
        or entity_description.key not in ETA_ENTITY_KEYS
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

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Explain the ETA without exposing historical GPS traces."""
        if self.entity_description.key != "stop_eta":
            return None
        result = self.student.eta_estimate or Estimate()
        timestamps = {
            "earliest_arrival": result.earliest_arrival,
            "latest_arrival": result.latest_arrival,
            "valid_until": result.valid_until,
            "estimated_arrival": result.arrival,
        }
        return {
            "status": self.student.eta_status,
            "announcements_allowed": self.student.eta_announcements_allowed,
            "period": self.student.eta_period,
            "source": result.source,
            "historical_trips": result.trips,
            "available_trips": result.available_trips,
            "matching_trips": result.matching_trips,
            "reason": result.reason,
            "confidence": result.confidence,
            **{
                name: stamp.isoformat() if stamp else None
                for name, stamp in timestamps.items()
            },
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.student.student_id in self.coordinator.data:
            self.student = self.coordinator.data[self.student.student_id]
            self.async_write_ha_state()
