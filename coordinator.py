"""Coordinator file for Here comes the bus Home assistant integration."""

from datetime import datetime, time, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import Const
from .data_update_entity import DataUpdateEntity
from .hcbapi import hcbapi
from .hcbapi.s1157 import Student

_LOGGER = logging.getLogger(__name__)
STUDENT_INFO = "student_info"
STOPS = "stops"
VEHICLE_LOCATION = "vehicle_location"


class HCBDataCoordinator(DataUpdateCoordinator[dict[str, DataUpdateEntity]]):
    """Define a data coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=Const.DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=15),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=False,
        )
        self.config_entry: ConfigEntry = config_entry
        self._school_id: str
        self._parent_id: str
        self._am_start_time: time = time(6, 0, 0)
        self._pm_start_time: time = time(14, 0, 0)
        self._current_day: int = dt_util.now().day
        self._am_stops_done: bool = 0
        self._pm_stops_done: bool = 0
        self.data = {}

    async def async_config_entry_first_refresh(self) -> None:
        """Handle the first refresh."""
        school = await hcbapi.get_school_info(self.config_entry.data["SchoolCode"])
        self._school_id = school.customer.id
        userInfo = await hcbapi.get_parent_info(
            self._school_id,
            self.config_entry.data["Username"],
            self.config_entry.data["Password"],
        )
        self._parent_id = userInfo.account.id
        am_times = []
        pm_times = []

        time_now = dt_util.now()  # local time
        for student in list[Student](userInfo.linked_students.student):
            self.data[student.entity_id] = DataUpdateEntity(student)
            am_stops_and_scans = await hcbapi.get_bus_info(
                self._school_id, self._parent_id, student.entity_id, hcbapi.AM_ID
            )
            pm_stops_and_scans = await hcbapi.get_bus_info(
                self._school_id, self._parent_id, student.entity_id, hcbapi.PM_ID
            )
            if am_stops_and_scans.student_stops is None:
                return
            am_times.append(
                am_stops_and_scans.student_stops.student_stop[0].tier_start_time.time()
            )
            pm_times.append(
                pm_stops_and_scans.student_stops.student_stop[0].tier_start_time.time()
            )

            if self._is_morning(time_now):
                self.data[
                    student.entity_id
                ].vehiclelocation = am_stops_and_scans.vehicle_location
            else:
                self.data[
                    student.entity_id
                ].vehiclelocation = pm_stops_and_scans.vehicle_location

        self._am_start_time = min(am_times)
        self._pm_start_time = min(pm_times)
        _LOGGER.debug("AM sart time: %s", self._am_start_time)
        _LOGGER.debug("PM sart time: %s", self._pm_start_time)

    async def _async_update_data(self) -> dict[str, DataUpdateEntity]:
        time_now = dt_util.now()  # local time
        time_of_day_id = hcbapi.AM_ID
        if not self._is_morning(time_now):
            time_of_day_id = hcbapi.PM_ID
        if not self._should_poll_data(time_now):
            return {}
        stops = []
        for studentId in self.data:
            student_stops = await hcbapi.get_bus_info(
                self._school_id, self._parent_id, studentId, time_of_day_id
            )

            if student_stops.student_stops is None:
                return {}
            self.data[studentId].vehiclelocation = student_stops.vehicle_location
            stops.extend(
                stop.arrival_time for stop in student_stops.student_stops.student_stop
            )

        self._set_stops_completed(time_now, stops)
        return self.data

    def _set_stops_completed(self, time_now, stops):
        stopsdone = all(item is not None for item in stops)
        if self._is_morning(time_now):
            self._am_stops_done = stopsdone
        else:
            self._pm_stops_done = stopsdone
            if self._pm_stops_done:
                self._current_day = time_now.day

    def _should_poll_data(self, time_now: datetime) -> bool:
        """Check to see if the time is when the bus is moving."""
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
            if self._is_morning(time_now) and self._am_stops_done:
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

    def _is_morning(self, time_now: datetime) -> bool:
        """Return if it is morning."""
        return time_now.hour < 12
