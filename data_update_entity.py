"""Define a data update entity."""

from .hcbapi import s1157, s1158


class DataUpdateEntity:
    """Define a data update entity."""

    def __init__(
        self,
        student: s1157.Student,
        vehicle_location: s1158.VehicleLocation = None,
        student_stops: s1158.StudentStop = None,
    ) -> None:
        """Initialize the data update entity."""
        self.student = student
        self.vehiclelocation = vehicle_location
        self.student_stops = student_stops
