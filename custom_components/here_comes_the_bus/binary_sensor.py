"""Support for Here comes the bus binary sensors."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ETA_ENTITY_KEYS
from .coordinator import HCBDataCoordinator
from .data import HCBConfigEntry, StudentData
from .entity import HCBEntity

type StateType = str | int | float | None
DEFAULT_ICON = "def_icon"


@dataclass(frozen=True, kw_only=True)
class HCBBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes binary sensor entities."""

    icon_on: str | None = None
    value_fn: Callable[[StudentData], bool | None]


def _message_code_to_bool(message_code: int | None) -> bool | None:
    """Format the message code to a boolean."""
    if message_code is None:
        return None
    return message_code in {1, 2}


ENTITY_DESCRIPTIONS: tuple[HCBBinarySensorEntityDescription, ...] = (
    HCBBinarySensorEntityDescription(
        key="ignition",
        name="Ignition on",
        icon="mdi:engine-off",
        icon_on="mdi:engine",
        value_fn=lambda x: x.ignition,
    ),
    HCBBinarySensorEntityDescription(
        key="display_on_map",
        name="Display on map",
        icon="mdi:map-marker-alert",
        icon_on="mdi:map-marker-check",
        value_fn=lambda x: x.display_on_map,
    ),
    HCBBinarySensorEntityDescription(
        key="message_code",
        name="In Service",
        icon="mdi:flag-off",
        icon_on="mdi:flag",
        value_fn=lambda x: _message_code_to_bool(x.message_code),
    ),
    HCBBinarySensorEntityDescription(
        key="stop_visit_inferred",
        name="Estimated pickup/drop-off",
        icon="mdi:bus-stop-uncovered",
        icon_on="mdi:bus-stop-covered",
        value_fn=lambda x: x.stop_visit_inferred,
    ),
    HCBBinarySensorEntityDescription(
        key="eta_announcements_allowed",
        name="Arrival announcements allowed",
        icon="mdi:volume-off",
        icon_on="mdi:volume-high",
        value_fn=lambda x: x.eta_announcements_allowed,
    ),
)


async def async_setup_entry(
    _: HomeAssistant,
    entry: HCBConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        HCBBinarySensor(entry.runtime_data.coordinator, entity_description, student)
        for entity_description in ENTITY_DESCRIPTIONS
        if entry.runtime_data.coordinator.eta_enabled
        or entity_description.key not in ETA_ENTITY_KEYS
        for student in entry.runtime_data.coordinator.data.values()
    )


class HCBBinarySensor(HCBEntity, BinarySensorEntity):
    """Defines a single bus sensor."""

    entity_description: HCBBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: HCBDataCoordinator,
        description: HCBBinarySensorEntityDescription,
        student: StudentData,
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, student, description)
        self._is_on: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        self._is_on = self.entity_description.value_fn(self.student)
        return self._is_on

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._is_on:
            return self.entity_description.icon_on
        return self.entity_description.icon

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Describe an inferred visit without claiming a confirmed badge scan."""
        if self.entity_description.key != "stop_visit_inferred":
            return None
        return {
            "period": self.student.eta_period,
            "assumed_on_bus": (self.student.eta_period == "am")
            if self.student.stop_visit_inferred is True
            and self.student.eta_period in ("am", "pm")
            else None,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.student.student_id in self.coordinator.data:
            self.student = self.coordinator.data[self.student.student_id]
            self.async_write_ha_state()
