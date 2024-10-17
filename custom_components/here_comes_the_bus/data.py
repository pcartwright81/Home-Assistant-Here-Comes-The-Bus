"""Custom types for here comes the bus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .coordinator import HCBDataCoordinator

type HCBConfigEntry = ConfigEntry[HCBData]


@dataclass
class HCBData:
    """Data for the Here comes the bus integration."""

    coordinator: HCBDataCoordinator
    integration: Integration


@dataclass
class StudentData:
    """Define a data update enitity."""

    def __init__(self, first_name: str, student_id: str) -> None:
        """Initialize the data update entity."""
        self.first_name: str = first_name
        self.student_id: str = student_id
        self.bus_name: str | None = None
        self.latitude: float | None = None
        self.longitude: float | None = None
        self.log_time: datetime | None = None
        self.ignition: bool | None = None
        self.latent: str | None = None
        self.heading: str | None = None
        self.speed: int | None = None
        self.address: str | None = None
        self.message_code: int | None = None
        self.display_on_map: bool | None = None
        self.am_arrival_time: datetime | None = None
        self.pm_arrival_time: datetime | None = None
        self.am_start_time: time = time(6, 0, 0)
        self.pm_start_time: time = time(14, 0, 0)

    def am_stops_done(self) -> bool:
        """Return true if the am stops are done."""
        if self.am_arrival_time is None:
            return False
        return self.am_arrival_time.hour != 0

    def pm_stops_done(self) -> bool:
        """Return true if the pm stops are done."""
        if self.pm_arrival_time is None:
            return False
        return self.pm_arrival_time.hour != 0
