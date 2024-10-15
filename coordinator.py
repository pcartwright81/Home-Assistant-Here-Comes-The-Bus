"""Coordinator file for Here comes the bus Home assistant integration."""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .defaults import Defaults
from .hcbapi import hcbapi
from .hcbapi.s1157 import Student
from .hcbapi.s1158 import StudentStop, VehicleLocation
from .student_data import StudentData
from dateutil import parser

_LOGGER = logging.getLogger(__name__)

class HCBDataCoordinator(DataUpdateCoordinator[dict[str, StudentData]]):
    """Define a data coordinator."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=Defaults.DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(
                seconds=config_entry.data.get(Defaults.UPDATE_INTERVAL, 20)
            ),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False,
        )
        self.config_entry = config_entry
        self._school_id: str
        self._parent_id: str

    async def async_config_entry_first_refresh(self) -> None:
        """Handle the first refresh."""
        school = await hcbapi.get_school_info(self.config_entry.data[Defaults.SCHOOL_CODE])
        self._school_id = school.customer.id
        userInfo = await hcbapi.get_parent_info(
            self._school_id,
            self.config_entry.data[Defaults.USERNAME],
            self.config_entry.data[Defaults.PASSWORD],
        )
        self._parent_id = userInfo.account.id
        self.data = {}
        for student in list[Student](userInfo.linked_students.student):
            student_update = StudentData(student.first_name, student.entity_id)
            self.data[student.entity_id] = student_update
            am_stops_and_scans = await hcbapi.get_bus_info(
                self._school_id, self._parent_id, student.entity_id, hcbapi.AM_ID
            )
            pm_stops_and_scans = await hcbapi.get_bus_info(
                self._school_id, self._parent_id, student.entity_id, hcbapi.PM_ID
            )
            # this gives the same info in am and pm, so don't need a check
            self._update_vehicle_location(
                student_update, am_stops_and_scans.vehicle_location
            )
            if am_stops_and_scans.student_stops is None:
                return
            am_stops = am_stops_and_scans.student_stops.student_stop
            pm_stops = pm_stops_and_scans.student_stops.student_stop
            student_update.am_start_time = am_stops[0].tier_start_time.time()
            student_update.pm_start_time = pm_stops[0].tier_start_time.time()
            self._update_stops(student_update, am_stops)
            self._update_stops(student_update, pm_stops)
            _LOGGER.debug(
                "Student %s am start time %r",
                student.first_name,
                student_update.am_start_time,
            )
            _LOGGER.debug(
                "Student %s pm start time %r",
                student.first_name,
                student_update.pm_start_time,
            )
            _LOGGER.debug(
                "Student %s am stops done %r",
                student.first_name,
                student_update.am_stops_done,
            )
            _LOGGER.debug(
                "Student %s pm stops done %r",
                student.first_name,
                student_update.pm_stops_done,
            )

    async def _async_update_data(self) -> dict[str, StudentData]:
        time_now = dt_util.now()  # local time
        time_of_day_id = hcbapi.AM_ID
        if not self._is_morning(time_now):
            time_of_day_id = hcbapi.PM_ID
        for student_id, student_update in self.data.items():
            if not self._should_poll_data(time_now, student_update):
                return {}
            student_stops = await hcbapi.get_bus_info(
                self._school_id, self._parent_id, student_id, time_of_day_id
            )
            self._update_vehicle_location(
                student_update, student_stops.vehicle_location
            )
            self._update_stops(student_update, student_stops)
        return self.data

    def _should_poll_data(
        self, time_now: datetime, student_update: StudentData
    ) -> bool:
        """Check to see if the time is when the bus is moving."""
        if time_now.weekday() >= 5:
            _LOGGER.debug("Not polling because it's the weekend")
            return 0
        if (
            time_now.time() < student_update.am_start_time
            or time_now.time() < student_update.pm_start_time
        ):
            _LOGGER.debug("Not polling because it's too early")
            return 0
        if (
            self._is_morning(time_now)
            and student_update.am_stops_done
            and student_update.log_time.day == time_now.day
        ):
            _LOGGER.debug(
                "Not polling %s because it's the morning and the am stops are done for the day",
                student_update.first_name,
            )
            return 0
        if student_update.pm_stops_done and student_update.log_time.day == time_now.day:
            _LOGGER.debug(
                "Not polling %s because it's the evening and the stops are done for the day",
                student_update.first_name,
            )
            return 0
        return 1

    def _is_morning(self, time_now: datetime) -> bool:
        """Return true if it is morning."""
        return time_now.hour < 12

    def _update_vehicle_location(
        self, student: StudentData, vehicle_location: VehicleLocation
    ):
        if vehicle_location is None:
            return
        student.address = vehicle_location.address
        student.bus_name = vehicle_location.name
        student.display_on_map = vehicle_location.display_on_map
        student.heading = vehicle_location.heading
        student.ignition = vehicle_location.ignition
        student.latent = vehicle_location.latent
        student.latitude = float(vehicle_location.latitude)
        student.longitude = float(vehicle_location.longitude)
        student.log_time = parser.parse(vehicle_location.log_time)
        student.message_code = vehicle_location.message_code
        student.speed = vehicle_location.speed

    def _update_stops(self, student: StudentData, stops: list[StudentStop]):
        if stops[0].time_of_day_id == hcbapi.AM_ID:
            # lamda function not working so...
            for stop in stops:
                if stop.stop_type == "School":
                    student.am_school_arrival_time = stop.arrival_time.time()
        else:
            # lamda function not working so...
            for stop in stops:
                if stop.stop_type != "School":
                    student.pm_stop_arrival_time = stop.arrival_time.time()
