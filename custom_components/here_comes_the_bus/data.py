"""Custom types for here comes the bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from datetime import datetime

    from hcb_soap_client.hcb_soap_client import HcbSoapClient
    from homeassistant.loader import Integration

    from .coordinator import HCBDataCoordinator
    from .eta import Estimate, Stop

type HCBConfigEntry = ConfigEntry[HCBData]


@dataclass
class HCBData:
    """Data for the Here comes the bus integration."""

    client: HcbSoapClient
    coordinator: HCBDataCoordinator
    integration: Integration


@dataclass
class StudentData:
    """Student data entity."""

    first_name: str
    student_id: str
    bus_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    log_time: datetime | None = None
    ignition: bool | None = None
    latent: bool | None = None
    heading: str | None = None
    speed: int | None = None
    address: str | None = None
    message_code: int | None = None
    display_on_map: bool | None = None
    am_school_arrival_time: time | None = None
    am_stop_arrival_time: time | None = None
    mid_school_arrival_time: time | None = None
    mid_stop_arrival_time: time | None = None
    pm_school_arrival_time: time | None = None
    pm_stop_arrival_time: time | None = None
    am_start_time: time = field(default_factory=lambda: time(6, 0))
    am_end_time: time = field(default_factory=lambda: time(9, 0))
    mid_start_time: time = field(default_factory=lambda: time(11, 0))
    mid_end_time: time = field(default_factory=lambda: time(13, 0))
    pm_start_time: time = field(default_factory=lambda: time(14, 0))
    pm_end_time: time = field(default_factory=lambda: time(16, 0))
    has_mid_stops: bool = False
    eta_stops: dict[str, Stop] = field(default_factory=dict)
    stop_eta: float | None = None
    eta_status: str = "unknown"
    eta_announcements_allowed: bool = False
    stop_visit_inferred: bool | None = None
    eta_estimate: Estimate | None = None
    eta_period: str | None = None
