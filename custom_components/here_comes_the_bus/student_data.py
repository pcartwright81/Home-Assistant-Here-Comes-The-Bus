"""Define a data update entity."""

from datetime import datetime, time


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
        self.am_arrival_time: datetime = None
        self.pm_arrival_time: datetime = None
        self.am_start_time: time = time(6, 0, 0)
        self.pm_start_time: time = time(14, 0, 0)

    def am_stops_done(self):
        """Return true if the am stops are done."""
        return self.am_arrival_time.hour != 0

    def pm_stops_done(self):
        """Return true if the pm stops are done."""
        return self.pm_arrival_time.hour != 0
