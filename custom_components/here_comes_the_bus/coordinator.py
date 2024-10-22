"""Coordinator file for Here comes the bus Home assistant integration."""

from calendar import SATURDAY
from datetime import datetime, timedelta

from hcb_soap_client.hcb_soap_client import HcbSoapClient
from hcb_soap_client.stop_response import StopResponse, StudentStop, VehicleLocation
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_SCHOOL_CODE, CONF_UPDATE_INTERVAL, DOMAIN, HMS, LOGGER
from .data import HCBConfigEntry, StudentData

_show_mock = False


class HCBDataCoordinator(DataUpdateCoordinator):
    """Define a data coordinator."""

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
        self._school_id: str
        self._parent_id: str
        self._client: HcbSoapClient = HcbSoapClient()
        self.config_entry = config_entry
        self.data: dict[str, StudentData]

    async def async_config_entry_first_refresh(self) -> None:
        """Handle the first refresh."""
        self._school_id = await self._client.get_school_id(
            self.config_entry.data[CONF_SCHOOL_CODE]
        )
        user_info = await self._client.get_parent_info(
            self._school_id,
            self.config_entry.data[CONF_USERNAME],
            self.config_entry.data[CONF_PASSWORD],
        )
        self._parent_id = user_info.account_id
        self.data = {}

        for student in user_info.students:
            student_data = StudentData(student.first_name, student.student_id)
            self.data[student.student_id] = student_data
            am_stops_and_scans: StopResponse = await self._client.get_stop_info(
                self._school_id,
                self._parent_id,
                student.student_id,
                HcbSoapClient.AM_ID,
            )
            pm_stops_and_scans: StopResponse = await self._client.get_stop_info(
                self._school_id,
                self._parent_id,
                student.student_id,
                HcbSoapClient.PM_ID,
            )
            # this gives the same info in am and pm, so don't need a check
            self._update_vehicle_location(
                student_data, am_stops_and_scans.vehicle_location
            )
            if len(pm_stops_and_scans.student_stops) == 0:
                # the api does not return data for anyone
                return
            am_stops = am_stops_and_scans.student_stops
            pm_stops = pm_stops_and_scans.student_stops
            student_data.am_start_time = am_stops[0].tier_start_time.time()
            student_data.pm_start_time = pm_stops[0].tier_start_time.time()
            self._update_stops(student_data, am_stops)
            self._update_stops(student_data, pm_stops)
            LOGGER.debug(
                "%s AM start time %r",
                student.first_name,
                student_data.am_start_time.strftime(HMS),
            )
            LOGGER.debug(
                "%s PM start time %r",
                student.first_name,
                student_data.pm_start_time.strftime(HMS),
            )
            LOGGER.debug(
                "%s AM stops done %r",
                student.first_name,
                student_data.am_stops_done(),
            )
            LOGGER.debug(
                "%s PM stops done %r",
                student.first_name,
                student_data.pm_stops_done(),
            )

    async def _async_update_data(self) -> dict[str, StudentData]:
        """
        Update student data asynchronously.

        This method retrieves the latest information about students' bus stops and
        vehicle locations from the Here Comes the Bus (HCB) service. It iterates
        through each student in the `data` dictionary, fetches their stop
        information for the relevant time of day (AM or PM), and updates the
        student's data with the retrieved information.

        Returns:
            A dictionary containing updated student data, where keys are student IDs
            and values are StudentData objects.

        """
        time_now = dt_util.now()  # Get the current local time

        # Determine the time of day ID (AM or PM)
        time_of_day_id = HcbSoapClient.PM_ID  # Default to PM
        if self._is_morning(time_now):
            time_of_day_id = HcbSoapClient.AM_ID

        # Iterate through each student and update their data
        for student_id, student_update in self.data.items():
            if not self._bus_is_moving(time_now, student_update):
                continue  # Skip if the bus is not moving for this student

            # Fetch stop information from the HCB service
            stops = await self._client.get_stop_info(
                self._school_id, self._parent_id, student_id, time_of_day_id
            )

            # Update the student's data with the retrieved information
            self._update_vehicle_location(student_update, stops.vehicle_location)
            self._update_stops(student_update, stops.student_stops)

        return self.data  # Return the updated data dictionary

    def _bus_is_moving(self, time_now: datetime, student_update: StudentData) -> bool:
        """
        Check if the bus is currently in operation (moving).

        This method determines if the school bus is actively transporting students
        based on the current time, the student's schedule, and whether they have
        completed their assigned stops for the day.

        Args:
            time_now: The current time as a datetime object.
            student_update: An object containing the student's data
                             (including their schedule and stop completion status).

        Returns:
            True if the bus is moving, False otherwise.

        """
        if _show_mock:
            return True

        if time_now.weekday() >= SATURDAY:
            LOGGER.debug("It's the weekend")
            return False

        if self._is_morning(time_now):
            if time_now.time() < student_update.am_start_time:
                LOGGER.debug(
                    "It's too early in the morning for %s", student_update.first_name
                )
                return False
            if self._am_stops_done_for_today(student_update, time_now):
                LOGGER.debug("AM stops are done for %s", student_update.first_name)
                return False
        elif self._pm_stops_done_for_today(
            student_update, time_now
        ):  # It's not morning
            LOGGER.debug("PM stops are done for %s", student_update.first_name)
            return False

        return True

    def _is_morning(self, time_now: datetime) -> bool:
        """Return True if it is morning."""
        _noon = 12  # Explicitly define noon
        return time_now.hour < _noon

    def _update_vehicle_location(
        self, student_data: StudentData, vehicle_location: VehicleLocation
    ) -> None:
        """
        Update the student's vehicle location data based on the VehicleLocation object.

        If vehicle_location is None and _show_mock_data is enabled, mock data is used.

        Args:
            student_data (StudentData): The student object to update with
            vehicle location.
            vehicle_location (VehicleLocation): The current location details of the bus.

        """
        if vehicle_location is not None:
            # Update student data from vehicle location
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
        elif _show_mock:
            # Use mock data if no vehicle location is provided and
            # _show_mock_data is True
            date_now = dt_util.now().replace(microsecond=0)

            student_data.address = "17606 Wall Triana Hwy"
            student_data.bus_name = "99-99"
            student_data.display_on_map = True
            student_data.heading = "E"
            student_data.ignition = True
            student_data.latent = False
            student_data.latitude = 34.807732
            student_data.longitude = -86.749863
            student_data.log_time = date_now
            student_data.message_code = 2
            student_data.speed = 100
            student_data.am_arrival_time = date_now.time()
            student_data.pm_arrival_time = date_now.time()

    def _update_stops(
        self, student_data: StudentData, stops: list[StudentStop]
    ) -> None:
        """
        Update the student's AM and PM arrival times based on the provided stops.

        Args:
            student_data (StudentData): The student whose arrival times are
            being updated.
            stops (list[StudentStop]): A list of stops to check for AM and PM times.

        """
        if _show_mock:
            return
        for stop in stops:
            # Check for school stop in the morning
            if (
                stop.stop_type == "School"
                and stop.time_of_day_id == HcbSoapClient.AM_ID
                and not student_data.am_stops_done()
            ):
                student_data.am_arrival_time = stop.arrival_time
                break

            # Check for regular stop in the afternoon
            if stop.stop_type == "Stop" and stop.time_of_day_id == HcbSoapClient.PM_ID:
                student_data.pm_arrival_time = stop.arrival_time
                break

    def _am_stops_done_for_today(
        self, student_data: StudentData, time_now: datetime
    ) -> bool:
        """
        Check if the student has completed their AM stops for today.

        Args:
            student_data: An object containing the student's data.
            time_now: The current time as a datetime object.

        Returns:
            True if AM stops are done for today, False otherwise.

        """
        return (
            student_data.am_stops_done()
            and student_data.log_time is not None
            and student_data.log_time.date() == time_now.date()
        )

    def _pm_stops_done_for_today(
        self, student_data: StudentData, time_now: datetime
    ) -> bool:
        """
        Check if the student has completed their PM stops for today.

        Args:
            student_data: An object containing the student's data.
            time_now: The current time as a datetime object.

        Returns:
            True if PM stops are done for today, False otherwise.

        """
        return (
            student_data.pm_stops_done()
            and student_data.log_time is not None
            and student_data.log_time.date() == time_now.date()
        )
