"""Custom types for here comes the bus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from datetime import datetime

    from hcb_soap_client.hcb_soap_client import HcbSoapClient
    from homeassistant.loader import Integration

    from .coordinator import HCBDataCoordinator

type HCBConfigEntry = ConfigEntry[HCBData]


@dataclass
class HCBData:
    """Data for the Here comes the bus integration."""

    client: HcbSoapClient
    coordinator: HCBDataCoordinator
    integration: Integration


@dataclass
class StudentData:
    """Define a data update enitity."""

    def __init__(  # noqa: PLR0913
        self,
        first_name: str,
        student_id: str,
        bus_name: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        log_time: datetime | None = None,
        ignition: bool | None = None,  # noqa: FBT001
        latent: bool | None = None,  # noqa: FBT001
        heading: str | None = None,
        speed: int | None = None,
        address: str | None = None,
        message_code: int | None = None,
        display_on_map: bool | None = None,  # noqa: FBT001
        am_school_arrival_time: time | None = None,
        am_stop_arrival_time: time | None = None,
        mid_school_arrival_time: time | None = None,
        mid_stop_arrival_time: time | None = None,
        pm_school_arrival_time: time | None = None,
        pm_stop_arrival_time: time | None = None,
        am_start_time: time = time(6, 0),  # Default value
        am_end_time: time = time(9, 0),  # Default value
        mid_start_time: time = time(11, 0),  # Default value
        mid_end_time: time = time(13, 0),  # Default value
        pm_start_time: time = time(14, 0),  # Default value
        pm_end_time: time = time(16, 0),  # Default value
        has_mid_stops: bool = False,  # Default value  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize the data update entity."""
        self.first_name = first_name
        self.student_id = student_id
        self.bus_name = bus_name
        self.latitude = latitude
        self.longitude = longitude
        self.log_time = log_time
        self.ignition = ignition
        self.latent = latent
        self.heading = heading
        self.speed = speed
        self.address = address
        self.message_code = message_code
        self.display_on_map = display_on_map
        self.am_school_arrival_time = am_school_arrival_time
        self.am_stop_arrival_time = am_stop_arrival_time
        self.mid_school_arrival_time = mid_school_arrival_time
        self.mid_stop_arrival_time = mid_stop_arrival_time
        self.pm_school_arrival_time = pm_school_arrival_time
        self.pm_stop_arrival_time = pm_stop_arrival_time
        self.am_start_time = am_start_time
        self.am_end_time = am_end_time
        self.mid_start_time = mid_start_time
        self.mid_end_time = mid_end_time
        self.pm_start_time = pm_start_time
        self.pm_end_time = pm_end_time
        self.has_mid_stops = has_mid_stops
