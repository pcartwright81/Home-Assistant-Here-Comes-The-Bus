"""Coordinator file for Here comes the bus Home assistant integration."""

from calendar import SATURDAY
from datetime import time, timedelta

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

        # first get the list of students and add them to the data
        for student in user_info.students:
            student_data = StudentData(student.first_name, student.student_id)
            self.data[student.student_id] = student_data

        # next get the stop info and set fields based what the api says
        for student_data in self.data.values():
            am_stops_and_scans: StopResponse = await self._client.get_stop_info(
                self._school_id,
                self._parent_id,
                student_data.student_id,
                self._get_time_of_day_id(time(7)),
            )
            pm_stops_and_scans: StopResponse = await self._client.get_stop_info(
                self._school_id,
                self._parent_id,
                student_data.student_id,
                self._get_time_of_day_id(time(14)),
            )
            # this gives the same info in am and pm, so don't need a check
            self._update_vehicle_location(
                student_data, am_stops_and_scans.vehicle_location
            )

            # the api does not return data for anyone try back after 5am
            if len(pm_stops_and_scans.student_stops) == 0:
                return
            # update the stops
            self._update_stops(student_data, am_stops_and_scans.student_stops)
            self._update_stops(student_data, pm_stops_and_scans.student_stops)

            # log the data
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
                student_data.am_arrival_time is not None,
            )
            LOGGER.debug(
                "%s PM stops done %r",
                student.first_name,
                student_data.pm_arrival_time is not None,
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
        # Iterate through each student and update their data
        for student_data in self.data.values():
            if not self._student_is_moving(student_data):
                return {}
            # Fetch stop information from the HCB service
            stops = await self._client.get_stop_info(
                self._school_id,
                self._parent_id,
                student_data.student_id,
                self._get_time_of_day_id(dt_util.now().time()),
            )
            # Update the student's data with the retrieved information
            self._update_vehicle_location(student_data, stops.vehicle_location)
            self._update_stops(student_data, stops.student_stops)

        return self.data  # Return the updated data dictionary

    @staticmethod
    def _student_is_moving(student_data: StudentData) -> bool:
        """Check to see if the student should be moving on the bus."""
        dt_now = dt_util.now()
        if dt_now.weekday() >= SATURDAY:
            LOGGER.debug("It's the weekend for %s", student_data.first_name)
            return False
        time_now = dt_now.time()
        if time_now <= time(12):
            if time_now < student_data.am_start_time:
                LOGGER.debug(
                    "It's too early in the morning for %s", student_data.first_name
                )
                return False
            if time_now >= time(9):
                LOGGER.debug("School has started")
        elif time_now >= time(12):
            if time_now < student_data.pm_start_time:
                LOGGER.debug(
                    "It's too early in the afternoon for %s", student_data.first_name
                )
                return False
            if time_now >= time(17):
                LOGGER.debug("It's too late for %s", student_data.first_name)
                return False
        LOGGER.debug("Updating data for %s", student_data.first_name)
        return True

    @staticmethod
    def _update_vehicle_location(
        student_data: StudentData, vehicle_location: VehicleLocation
    ) -> None:
        if vehicle_location is not None:
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
            return
        if _show_mock is False:
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
            return
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

    @staticmethod
    def _update_stops(student_data: StudentData, stops: list[StudentStop]) -> None:
        if _show_mock:
            return
        for stop in stops:
            # Check for school stop in the morning
            if (
                stop.stop_type == "School"
                and stop.time_of_day_id == HcbSoapClient.AM_ID
            ):
                student_data.am_arrival_time = HCBDataCoordinator._fix_time(
                    stop.arrival_time
                )
                student_data.am_start_time = stop.tier_start_time
                break

            # Check for regular stop in the afternoon
            if stop.stop_type == "Stop" and stop.time_of_day_id == HcbSoapClient.PM_ID:
                student_data.pm_arrival_time = HCBDataCoordinator._fix_time(
                    stop.arrival_time
                )
                student_data.pm_start_time = stop.tier_start_time
                break

    @staticmethod
    def _fix_time(input_time: time | None) -> time | None:
        """Make 00:00 appear as none, and replace microseconds."""
        if input_time is None:
            return None
        if input_time == time(0):
            return None
        return input_time.replace(microsecond=0)

    @staticmethod
    def _get_time_of_day_id(check_time: time) -> str:
        """Get the time of day id right now."""
        # before 10 is morning
        if check_time < time(10):
            return "55632A13-35C5-4169-B872-F5ABDC25DF6A"
        # between 10 and 13:30 is mid
        if check_time > time(10) and check_time < time(13, 30):
            return "27AADCA0-6D7E-4247-A80F-7847C448EEED"
        # default to night
        return "6E7A050E-0295-4200-8EDC-3611BB5DE1C1"
