"""Coordinator file for Here comes the bus Home assistant integration."""

from calendar import SATURDAY
from datetime import datetime, time, timedelta

from hcb_soap_client.stop_response import StudentStop, VehicleLocation
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_SCHOOL_CODE, CONF_UPDATE_INTERVAL, DOMAIN, LOGGER
from .data import HCBConfigEntry, StudentData


class HCBDataCoordinator(DataUpdateCoordinator):
    """Define a data coordinator."""

    AM_ID = "55632A13-35C5-4169-B872-F5ABDC25DF6A"
    MID_ID = "27AADCA0-6D7E-4247-A80F-7847C448EEED"
    PM_ID = "6E7A050E-0295-4200-8EDC-3611BB5DE1C1"

    def __init__(self, hass: HomeAssistant, config_entry: HCBConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(
                seconds=config_entry.data.get(CONF_UPDATE_INTERVAL, 20)
            ),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True,  # This has to be true.  But why?
        )
        self._school_id: str = ""
        self._parent_id: str = ""
        self.config_entry = config_entry
        self.data: dict[str, StudentData]

    async def async_config_entry_first_refresh(self) -> None:
        """Handle the first refresh."""
        if self._school_id == "":
            self._school_id = await self.config_entry.runtime_data.client.get_school_id(
                self.config_entry.data[CONF_SCHOOL_CODE]
            )
        if self._parent_id == "":
            user_info = await self.config_entry.runtime_data.client.get_parent_info(
                self._school_id,
                self.config_entry.data[CONF_USERNAME],
                self.config_entry.data[CONF_PASSWORD],
            )
            self._parent_id = user_info.account_id
            self.data = {}
            # first get the list of students and add them to the data
            for student in user_info.students:
                student_data = StudentData(student.first_name, student.student_id)
                self.data[student.student_id] = student_data
        try:
            #this fails during epecific hours
            for student_data in self.data.values():
                # next get the stops for each time.
                for time_of_day in user_info.times:
                    stop_response = (
                        await self.config_entry.runtime_data.client.get_stop_info(
                            self._school_id,
                            self._parent_id,
                            student_data.student_id,
                            time_of_day.id,
                        )
                    )
                    if time_of_day.id == self.AM_ID:
                        self._update_vehicle_location(
                            student_data, stop_response.vehicle_location
                        )
                    elif time_of_day.id == self.MID_ID:
                        student_data.has_mid_stops = any(stop_response.student_stops)
                        if not student_data.has_mid_stops:
                            continue
                    self._update_stops(student_data, stop_response.student_stops)
        except ValueError as e:
            LOGGER.error(e)
        LOGGER.debug("Initialization Complete")

    async def _async_update_data(self) -> dict[str, StudentData]:
        # Iterate through each student and update their data
        for student_data in self.data.values():
            if not self._student_is_moving(student_data):
                continue
            # Fetch stop information from the HCB service
            stops = await self.config_entry.runtime_data.client.get_stop_info(
                self._school_id,
                self._parent_id,
                student_data.student_id,
                self._get_time_of_day_id(dt_util.now().time()),
            )
            # Update the student's data with the retrieved information
            self._update_vehicle_location(student_data, stops.vehicle_location)
            self._update_stops(student_data, stops.student_stops)

        return self.data  # Return the updated data dictionary

    def _student_is_moving(self, student_data: StudentData) -> bool:
        """Check to see if the student should be moving on the bus."""
        dt_now = dt_util.now()
        time_now = dt_now.time()

        if dt_now.weekday() >= SATURDAY:
            return False
        if self._is_am(time_now):
            return student_data.am_start_time <= time_now <= student_data.am_end_time
        if self._is_mid(time_now):
            if not student_data.has_mid_stops:
                return False
            return student_data.mid_start_time <= time_now <= student_data.mid_end_time

        return student_data.pm_start_time <= time_now <= student_data.pm_end_time

    def _update_vehicle_location(
        self, student_data: StudentData, vehicle_location: VehicleLocation | None
    ) -> None:
        """Update student data with the provided vehicle location information."""
        if vehicle_location:
            student_data.address = vehicle_location.address
            student_data.bus_name = vehicle_location.name
            student_data.display_on_map = vehicle_location.display_on_map
            student_data.heading = vehicle_location.heading
            student_data.ignition = vehicle_location.ignition
            student_data.latent = vehicle_location.latent
            student_data.latitude = vehicle_location.latitude
            student_data.longitude = vehicle_location.longitude
            student_data.log_time = vehicle_location.log_time.replace(
                tzinfo=dt_util.now().tzinfo
            )
            student_data.message_code = vehicle_location.message_code
            student_data.speed = vehicle_location.speed
        else:
            student_data.address = None
            student_data.bus_name = None
            student_data.display_on_map = None
            student_data.heading = None
            student_data.ignition = None
            student_data.latent = None
            student_data.latitude = None
            student_data.longitude = None
            student_data.log_time = None
            student_data.message_code = None
            student_data.speed = None

    def _update_stops(
        self, student_data: StudentData, stops: list[StudentStop]
    ) -> None:
        """Update student data with information from the provided stops."""
        if not stops or len(stops) == 0:
            msg = "No stops returned."
            raise ValueError(msg)
        if any(stop.time_of_day_id != stops[0].time_of_day_id for stop in stops):
            msg = "Time of day must match for this function to work"
            raise ValueError(msg)
        school = "School"
        stop = "Stop"
        if stops[0].time_of_day_id == HCBDataCoordinator.AM_ID:
            student_data.am_start_time = self._get_start_time(stops)
            student_data.am_end_time = self._get_end_time(stops)
            student_data.am_school_arrival_time = self._get_stop_time(stops, school)
            student_data.am_stop_arrival_time = self._get_stop_time(stops, stop)
            return
        if stops[0].time_of_day_id == HCBDataCoordinator.MID_ID:
            student_data.mid_start_time = self._get_start_time(stops)
            student_data.mid_end_time = self._get_end_time(stops)
            student_data.mid_school_arrival_time = self._get_stop_time(stops, school)
            student_data.mid_stop_arrival_time = self._get_stop_time(stops, stop)
            return
        if stops[0].time_of_day_id == HCBDataCoordinator.PM_ID:
            student_data.pm_start_time = self._get_start_time(stops)
            student_data.pm_end_time = self._get_end_time(stops)
            student_data.pm_school_arrival_time = self._get_stop_time(stops, school)
            student_data.pm_stop_arrival_time = self._get_stop_time(stops, stop)

    def _get_time_of_day_id(self, check_time: time) -> str:
        """Get the time of day ID based on the given time."""
        if self._is_am(check_time):
            return HCBDataCoordinator.AM_ID
        if self._is_mid(check_time):
            return HCBDataCoordinator.MID_ID
        return HCBDataCoordinator.PM_ID

    def _get_start_time(self, stops: list[StudentStop]) -> time:
        earliest = min(stop.start_time for stop in stops)
        # Convert time to datetime to perform the addition
        dummy_date = dt_util.now().date()  # Use any date, it doesn't matter for this
        datetime_with_time = datetime.combine(dummy_date, earliest)

        # Add 30 minutes
        new_datetime = datetime_with_time - timedelta(minutes=30)

        # Extract the time component from the new datetime
        return new_datetime.time()

    def _get_end_time(self, stops: list[StudentStop]) -> time:
        latest = max(stop.start_time for stop in stops)
        # Convert time to datetime to perform the addition
        dummy_date = dt_util.now().date()  # Use any date, it doesn't matter for this
        datetime_with_time = datetime.combine(dummy_date, latest)

        # Add 30 minutes
        new_datetime = datetime_with_time + timedelta(minutes=30)

        # Extract the time component from the new datetime
        return new_datetime.time()

    def _get_stop_time(self, stops: list[StudentStop], stop_type: str) -> time | None:
        stop_stops = [stop for stop in stops if stop.stop_type == stop_type]
        return self._fix_time(stop_stops[0].arrival_time)

    def _is_am(self, check_time: time) -> bool:
        """Return True if the time is between midnight and 10:00 AM, False otherwise."""
        return time(0) <= check_time < time(10)

    def _is_mid(self, check_time: time) -> bool:
        """Return True if the time is between 10:00 AM and 1:30 PM, False otherwise."""
        return time(10) <= check_time < time(13, 30)

    def _is_pm(self, check_time: time) -> bool:
        """Return True if the time is between 1:30 PM and midnight, False otherwise."""
        return time(13, 30) <= check_time <= time(23, 59, 59)

    def _fix_time(self, input_time: time | None) -> time | None:
        """
        Make the time better for a sensor.

        If input_time is None or 00:00:00, return None.
        Otherwise, return input_time with microseconds set to 0.
        """
        if input_time is None or input_time == time(0):
            return None
        return input_time.replace(microsecond=0)
