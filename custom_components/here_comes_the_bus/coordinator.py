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

_noon = 12
_five_am = 5
_five_pm = 17


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
            always_update=False,
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
            student_update = StudentData(student.first_name, student.student_id)
            self.data[student.student_id] = student_update
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
            if pm_stops_and_scans.student_stops is None:
                LOGGER.debug("API has cleared most of the data right now.")
                return
            # this gives the same info in am and pm, so don't need a check
            self._update_vehicle_location(
                student_update, am_stops_and_scans.vehicle_location
            )
            am_stops = am_stops_and_scans.student_stops
            pm_stops = pm_stops_and_scans.student_stops
            student_update.am_start_time = am_stops[0].tier_start_time.time()
            student_update.pm_start_time = pm_stops[0].tier_start_time.time()
            self._update_stops(student_update, am_stops)
            self._update_stops(student_update, pm_stops)
            LOGGER.debug(
                "%s AM start time %r",
                student.first_name,
                student_update.am_start_time.strftime(HMS),
            )
            LOGGER.debug(
                "%s PM start time %r",
                student.first_name,
                student_update.pm_start_time.strftime(HMS),
            )
            LOGGER.debug(
                "%s AM stops done %r",
                student.first_name,
                student_update.am_stops_done(),
            )
            LOGGER.debug(
                "%s PM stops done %r",
                student.first_name,
                student_update.pm_stops_done(),
            )

    async def _async_update_data(self) -> dict[str, StudentData]:
        time_now = dt_util.now()  # local time
        time_of_day_id = HcbSoapClient.AM_ID
        if not self._is_morning(time_now):
            time_of_day_id = HcbSoapClient.PM_ID
        for student_id, student_update in self.data.items():
            if not self._should_poll_data(time_now, student_update):
                continue
            stops = await self._client.get_stop_info(
                self._school_id, self._parent_id, student_id, time_of_day_id
            )
            self._update_vehicle_location(student_update, stops.vehicle_location)
            self._update_stops(student_update, stops.student_stops)
        return self.data

    def _should_poll_data(
        self, time_now: datetime, student_update: StudentData
    ) -> bool:
        """Check to see if the time is when the bus is moving."""
        if time_now.weekday() >= SATURDAY:
            LOGGER.debug("It's the weekend")
            return False
        if time_now.hour < _five_am or time_now.hour > _five_pm:
            LOGGER.debug("It's before 5 or after 5")
            return False
        if self._is_morning(time_now) and (
            time_now.time() < student_update.am_start_time
        ):
            LOGGER.debug(
                "It's too early in the morning for %s",
                student_update.first_name,
            )
            return False

        if self._is_morning(time_now) and student_update.am_stops_done():
            LOGGER.debug("AM stops are done for %s", student_update.first_name)
            return False

        if not self._is_morning(time_now) and student_update.pm_stops_done():
            LOGGER.debug("PM stops are done for %s", student_update.first_name)
            return False
        return True

    def _is_morning(self, time_now: datetime) -> bool:
        """Return true if it is morning."""
        return time_now.hour < _noon

    def _update_vehicle_location(
        self, student: StudentData, vehicle_location: VehicleLocation
    ) -> None:
        if vehicle_location is None:
            return
        student.address = vehicle_location.address
        student.bus_name = vehicle_location.name
        student.display_on_map = vehicle_location.display_on_map
        student.heading = vehicle_location.heading
        student.ignition = vehicle_location.ignition
        student.latent = vehicle_location.latent
        student.latitude = vehicle_location.latitude
        student.longitude = vehicle_location.longitude
        student.log_time = vehicle_location.log_time
        student.message_code = vehicle_location.message_code
        student.speed = vehicle_location.speed

    def _update_stops(self, student: StudentData, stops: list[StudentStop]) -> None:
        for stop in stops:
            if (
                stop.stop_type == "School"
                and stop.time_of_day_id == HcbSoapClient.AM_ID
            ):
                student.am_arrival_time = stop.arrival_time
                break
            if stop.stop_type == "Stop" and stop.time_of_day_id == HcbSoapClient.PM_ID:
                student.pm_arrival_time = stop.arrival_time
                break
