"""Coordinator file for Here comes the bus Home assistant integration."""

from datetime import datetime, time, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .hcbapi.hcbapi import AM_ID, PM_ID, get_bus_info, get_parent_info, get_school_info
from .hcbapi.s1157 import Student
from .hcbapi.s1158 import VehicleLocation

_LOGGER = logging.getLogger(__name__)


class HCBDataCoordinator(DataUpdateCoordinator):
    """Define a data coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=15),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False,
        )
        self.config = entry.data
        self._school_id: str
        self._parent_id: str
        self._students: list[Student]
        self._am_start_time: time = time(6, 0, 0)
        self._pm_start_time: time = time(14, 0, 0)
        self._initialized: bool
        self._current_day: int
        self._am_stops_done: bool
        self._pm_stops_done: bool
        self._done_for_day: bool
        self.data = []

    async def async_config_entry_first_refresh(self) -> None:
        """Handle the first refresh."""
        school = await get_school_info(self.config["SchoolCode"])
        self._school_id = school.customer.id
        userInfo = await get_parent_info(
            self._school_id, self.config["Username"], self.config["Password"]
        )
        self._parent_id = userInfo.account.id
        self._students = userInfo.linked_students.student
        am_times = []
        pm_times = []

        for student in self._students:
            student_data = DataUpdateEntity(student, None)
            self.data.append(student_data)
            am_stops_and_scans = await get_bus_info(
                self._school_id, self._parent_id, student.entity_id, AM_ID
            )
            pm_stops_and_scans = await get_bus_info(
                self._school_id, self._parent_id, student.entity_id, PM_ID
            )
            if am_stops_and_scans.student_stops is None:
                return
            am_times.append(
                am_stops_and_scans.student_stops.student_stop[0].tier_start_time.time()
            )
            pm_times.append(
                pm_stops_and_scans.student_stops.student_stop[0].tier_start_time.time()
            )

            time_now = dt_util.now()  # local time
            if time_now.hour < 12:
                student_data.vehiclelocation = am_stops_and_scans.vehicle_location
            else:
                student_data.vehiclelocation = pm_stops_and_scans.vehicle_location

        self._am_start_time = min(am_times)
        self._pm_start_time = min(pm_times)
        _LOGGER.debug("AM sart time: %s", self._am_start_time)
        _LOGGER.debug("PM sart time: %s", self._pm_start_time)

    async def _async_update_data(self) -> None:
        time_now = dt_util.now()  # local time
        time_of_day_id = AM_ID
        if time_now.hour >= 12:
            time_of_day_id = PM_ID

        if not self._should_poll_data(time_now):
            return None
        stops = []
        data = []
        for student in self._students:
            student_stops = await get_bus_info(
                self._school_id, self._parent_id, student.entity_id, time_of_day_id
            )

            if student_stops.student_stops is None:
                return None

            data.append(DataUpdateEntity(student, student_stops.vehicle_location))
            stops.extend(
                stop.arrival_time for stop in student_stops.student_stops.student_stop
            )

        self._set_stops_completed(time_now, stops)
        return data

    def _set_stops_completed(self, time_now, stops):
        stopsdone = all(item is not None for item in stops)
        if time_now.hour < 12:
            self._am_stops_done = stopsdone
        else:
            self._pm_stops_done = stopsdone
            if self._pm_stops_done:
                self._current_day = time_now.day

    def _should_poll_data(self, time_now: datetime) -> bool:
        if time_now.weekday() >= 5:
            _LOGGER.debug("Not polling because it's the weekend!")
            return 0
        if (
            time_now.time() < self._am_start_time
            or time_now.time() < self._pm_start_time
        ):
            _LOGGER.debug("Not polling because it's too early")
            return 0
        if self._current_day == time_now.day:  # same day do more logic
            if time_now.hour < 12 and self._am_stops_done:
                _LOGGER.debug(
                    "Not polling because it's the morning and the stops are done"
                )
                return 0
            if self._pm_stops_done:
                _LOGGER.debug(
                    "Not polling because it's the evening and the stops are done"
                )
                return 0
        return 1


class DataUpdateEntity:
    """Define a data update entity."""

    def __init__(self, student: Student, vehicle_location: VehicleLocation) -> None:
        """Initialize the data update entity."""
        self.student = student
        self.vehiclelocation = vehicle_location
