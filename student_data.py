"""Define a data update entity."""

from datetime import datetime, time

_no_time = time(0, 0, 0)


class StudentData:
    """Define a data update enitity."""

    def __init__(self, first_name: str, student_id: str) -> None:
        """Initialize the data update entity."""
        self.first_name: str = first_name
        self.student_id: str = student_id
        self.bus_name: str = None
        self.latitude: float = None
        self.longitude: float = None
        self.log_time: datetime = None
        self.ignition: bool = None
        self.latent: str = None
        self.heading: str = None
        self.speed: int = None
        self.address: str = None
        self.message_code: str = None
        self.display_on_map: bool = None
        self.am_school_arrival_time: time = None
        self.pm_stop_arrival_time: time = None
        self.am_start_time: time = time(6, 0, 0)
        self.pm_start_time: time = time(14, 0, 0)
        self.am_stops_done: bool = self.am_school_arrival_time != _no_time
        self.pm_stops_done: bool = self.pm_stop_arrival_time != _no_time
