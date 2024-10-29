"""Support for Here comes the bus binary sensors."""

from collections.abc import Callable

from attr import dataclass
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import HCBDataCoordinator
from .data import HCBConfigEntry, StudentData
from .entity import HCBEntity

type StateType = str | int | float | None
DEFAULT_ICON = "def_icon"


@dataclass(frozen=True, kw_only=True)
class HCBBinarySensorEntityDescription(
    BinarySensorEntityDescription, frozen_or_thawed=True
):
    """A class that describes binary sensor entities."""

    icon_on: str | None = None
    value_fn: Callable[[StudentData], bool | None] | None = None


def _message_code_to_bool(message_code: int | None) -> bool | None:
    """Format the message code to a boolean."""
    if message_code is None:
        return None
    return message_code == 1


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
        value_fn=lambda x: _message_code_to_bool(x.message_code),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: HCBConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    async_add_entities(
        HCBBinarySensor(entry.runtime_data.coordinator, entity_description, student)
        for entity_description in ENTITY_DESCRIPTIONS
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
        if self.entity_description.value_fn is not None:
            self._is_on = self.entity_description.value_fn(self.student)
        return self._is_on

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        if self._is_on:
            return self.entity_description.icon_on
        return super().icon

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if len(self.coordinator.data) == 0:
            return
        self.student = self.coordinator.data[self.student.student_id]
        self.async_write_ha_state()
