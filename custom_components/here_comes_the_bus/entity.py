"""HCB class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BUS, DOMAIN, HERE_COMES_THE_BUS
from .coordinator import HCBDataCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription

    from .data import StudentData


class HCBEntity(CoordinatorEntity[HCBDataCoordinator]):
    """HCB class."""

    def __init__(
        self,
        coordinator: HCBDataCoordinator,
        student: StudentData,
        description: EntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.student = student
        self.entity_description = description
        self.use_device_name = True
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, student.student_id)},
            manufacturer=HERE_COMES_THE_BUS,
            name=f"{student.first_name} {BUS}",
        )

    @property
    def name(self) -> str | None:
        """Return the name of this device."""
        return f"{self.student.first_name} {BUS} {self.entity_description.name}"

    @property
    def unique_id(self) -> str | None:
        """Return a unique identifier for this sensor."""
        return f"{self.student.first_name}_{BUS}_{self.entity_description.key}".lower()

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        return "mdi:bus"
