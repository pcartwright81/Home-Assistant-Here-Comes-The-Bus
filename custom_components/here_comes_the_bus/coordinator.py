"""Coordinator file for Here comes the bus Home assistant integration."""

import json
from calendar import SATURDAY
from dataclasses import replace
from datetime import datetime, time, timedelta
from enum import StrEnum

from hcb_soap_client.stop_response import StudentStop, VehicleLocation
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ARRIVAL_ESTIMATES,
    CONF_DIRECTIONS,
    CONF_INFER_STOP,
    CONF_SCHOOL_CODE,
    CONF_STOP_ANNOUNCEMENTS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ETA_OPTIONS,
    DOMAIN,
    LOGGER,
)
from .data import HCBConfigEntry, StudentData
from .eta import (
    DIRECTION_DEGREES,
    MAX_AGE,
    MAX_GAP,
    Estimate,
    Journey,
    Point,
    Stop,
    completed_trip,
    reported_trip,
    street_name,
    valid_coordinates,
)
from .eta_history import History


class TimeOfDay(StrEnum):
    """Time of day identifiers from HCB service."""

    AM = "55632A13-35C5-4169-B872-F5ABDC25DF6A"
    MID = "27AADCA0-6D7E-4247-A80F-7847C448EEED"
    PM = "6E7A050E-0295-4200-8EDC-3611BB5DE1C1"


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
        self._school_id: str = ""
        self._parent_id: str = ""
        self.config_entry = config_entry
        self.data: dict[str, StudentData]
        self.eta_enabled = (
            config_entry.options.get(
                CONF_ARRIVAL_ESTIMATES, DEFAULT_ETA_OPTIONS[CONF_ARRIVAL_ESTIMATES]
            )
            is not False
        )
        self.eta_history = (
            History(hass, config_entry.entry_id) if self.eta_enabled else None
        )
        self._eta_journeys: dict[tuple, Journey] = {}
        self._eta_suppressed: set[str] = set()
        self._eta_arrived: set[str] = set()
        self._eta_reported: set[str] = set()
        self._eta_reports: dict[str, time | None] = {}
        self._eta_store = (
            Store(hass, 1, f"{DOMAIN}.eta_completed.{config_entry.entry_id}")
            if self.eta_enabled
            else None
        )
        self._eta_day = None
        self._eta_save_pending = False

    async def async_config_entry_first_refresh(self) -> None:  # noqa: PLR0912
        """Handle the first refresh."""
        if self.eta_enabled:
            await self._async_load_eta_completion()
        user_info = None
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
        else:
            user_info = await self.config_entry.runtime_data.client.get_parent_info(
                self._school_id,
                self.config_entry.data[CONF_USERNAME],
                self.config_entry.data[CONF_PASSWORD],
            )
            if not hasattr(self, "data") or self.data is None:
                self.data = {}
                for student in user_info.students:
                    student_data = StudentData(student.first_name, student.student_id)
                    self.data[student.student_id] = student_data
        try:
            # this fails during specific hours
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
                    if time_of_day.id == TimeOfDay.AM:
                        self._update_vehicle_location(
                            student_data, stop_response.vehicle_location
                        )
                    elif time_of_day.id == TimeOfDay.MID:
                        student_data.has_mid_stops = any(stop_response.student_stops)
                        if not student_data.has_mid_stops:
                            continue
                    self._update_stops(student_data, stop_response.student_stops)
        except ValueError as e:
            LOGGER.error(e)
        LOGGER.debug("Initialization Complete")
        for student in self.data.values():
            await self._async_update_eta(student)

    async def _async_update_data(self) -> dict[str, StudentData]:
        # Iterate through each student and update their data
        for student_data in self.data.values():
            if not self._student_is_moving(student_data):
                await self._async_update_eta(student_data)
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
            await self._async_update_eta(student_data)

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
            LOGGER.debug(
                "No stops assigned for student %s; skipping stop-time update",
                student_data.first_name,
            )
            return
        if any(stop.time_of_day_id != stops[0].time_of_day_id for stop in stops):
            msg = "Time of day must match for this function to work"
            raise ValueError(msg)
        if self.eta_enabled:
            self._update_eta_stop(student_data, stops)
        school = "School"
        stop = "Stop"
        if stops[0].time_of_day_id == TimeOfDay.AM:
            student_data.am_start_time = self._get_start_time(stops)
            student_data.am_end_time = self._get_end_time(stops)
            student_data.am_school_arrival_time = self._get_stop_time(stops, school)
            student_data.am_stop_arrival_time = self._get_stop_time(stops, stop)
            return
        if stops[0].time_of_day_id == TimeOfDay.MID:
            student_data.mid_start_time = self._get_start_time(stops)
            student_data.mid_end_time = self._get_end_time(stops)
            student_data.mid_school_arrival_time = self._get_stop_time(stops, school)
            student_data.mid_stop_arrival_time = self._get_stop_time(stops, stop)
            return
        if stops[0].time_of_day_id == TimeOfDay.PM:
            student_data.pm_start_time = self._get_start_time(stops)
            student_data.pm_end_time = self._get_end_time(stops)
            student_data.pm_school_arrival_time = self._get_stop_time(stops, school)
            student_data.pm_stop_arrival_time = self._get_stop_time(stops, stop)
            return
        msg = "Invalid time of day ID. Cannot update stops."
        raise ValueError(msg)

    def _update_eta_stop(self, student: StudentData, stops: list[StudentStop]) -> None:
        """Keep destination identity separate from reported actual arrival times."""
        periods = {TimeOfDay.AM: "am", TimeOfDay.MID: "mid", TimeOfDay.PM: "pm"}
        period = periods.get(stops[0].time_of_day_id)
        if period is None:
            return
        student.eta_stops.pop(period, None)
        destination = next((stop for stop in stops if stop.stop_type == "Stop"), None)
        if destination is None:
            return
        if not isinstance(destination.latitude, int | float) or not isinstance(
            destination.longitude, int | float
        ):
            return
        if valid_coordinates(destination.latitude, destination.longitude):
            student.eta_stops[period] = Stop(
                str(destination.stop_id),
                destination.latitude,
                destination.longitude,
                self._get_start_time(stops),
                self._get_end_time(stops),
            )

    async def _async_load_eta_completion(self) -> None:
        """Restore today's completed visits so restarts cannot rearm alerts."""
        try:
            saved = await self._eta_store.async_load() or {}
        except OSError:
            LOGGER.warning("Unable to read bus ETA completion state", exc_info=True)
            return
        today = dt_util.now().date()
        if saved.get("day") == today.isoformat():
            self._eta_day = today
            self._eta_arrived = set(saved.get("visits", []))
            self._eta_reported = set(saved.get("reported", []))
            self._eta_suppressed = set(saved.get("suppressed", []))

    def _reset_eta_cycle(self, now: datetime) -> None:
        """Drop runtime state at the next local day."""
        if self._eta_day != now.date():
            self._eta_journeys.clear()
            self._eta_suppressed.clear()
            self._eta_arrived.clear()
            self._eta_reported.clear()
            self._eta_reports.clear()
            self._eta_day = now.date()

    def _set_eta_done(
        self, student: StudentData, trips: int = 0, *, reported: bool = False
    ) -> None:
        """Expose a latched completion separately from an unknown ETA."""
        student.stop_eta = 0.0
        student.stop_visit_inferred = None if reported else True
        student.eta_status = "done"
        student.eta_announcements_allowed = False
        student.eta_estimate = Estimate(
            source="reported_arrival" if reported else "inferred_stop",
            trips=trips,
            available_trips=trips,
            reason="completed",
        )

    async def _async_save_eta_completion(
        self, now: datetime, *, retry: bool = False
    ) -> None:
        """Persist both latches independently; silence does not imply boarding."""
        if retry and not self._eta_save_pending:
            return
        self._eta_save_pending = True
        try:
            await self._eta_store.async_save(
                {
                    "day": now.date().isoformat(),
                    "visits": sorted(self._eta_arrived),
                    "reported": sorted(self._eta_reported),
                    "suppressed": sorted(self._eta_suppressed),
                }
            )
        except OSError:
            LOGGER.warning(
                "Unable to save bus ETA completion state; will retry next update",
                exc_info=True,
            )
        else:
            self._eta_save_pending = False

    def _eta_options(
        self, student: StudentData, period: str
    ) -> tuple[bool, bool, float | None]:
        """Resolve shared switches and this student's period-specific direction."""
        infer_stop = (
            self.config_entry.options.get(
                CONF_INFER_STOP, DEFAULT_ETA_OPTIONS[CONF_INFER_STOP]
            )
            is True
        )
        stop_announcements = (
            self.config_entry.options.get(
                CONF_STOP_ANNOUNCEMENTS, DEFAULT_ETA_OPTIONS[CONF_STOP_ANNOUNCEMENTS]
            )
            is True
        )
        override = DIRECTION_DEGREES.get(
            self.config_entry.options.get(CONF_DIRECTIONS, {})
            .get(student.student_id, {})
            .get(period)
        )
        return infer_stop, stop_announcements, override

    async def _async_update_eta(  # noqa: PLR0911, PLR0915
        self, student: StudentData
    ) -> None:
        """Compute the active trip countdown without making extra cloud requests."""
        if not self.eta_enabled:
            return
        now = dt_util.now()
        student.stop_eta = None
        student.eta_announcements_allowed = False
        student.eta_status = "unknown"
        student.eta_estimate = Estimate()
        student.eta_period = None
        student.stop_visit_inferred = None
        if "recorder" not in self.hass.config.components:
            student.eta_estimate = Estimate(reason="recorder_disabled")
            return
        self._reset_eta_cycle(now)
        await self._async_save_eta_completion(now, retry=True)
        moving = self._student_is_moving(student)
        period = (
            "am"
            if self._is_am(now.time())
            else "mid"
            if self._is_mid(now.time())
            else "pm"
        )
        if not moving:
            elapsed = [
                (stop.start, name)
                for name, stop in student.eta_stops.items()
                if stop.start <= now.time()
            ]
            period = max(elapsed)[1] if elapsed else period
        stop = student.eta_stops.get(period)
        if stop is None:
            student.eta_estimate = Estimate(reason="no_destination")
            return
        student.eta_period = period
        key = (student.student_id, period, stop)
        completion_key = json.dumps(
            (student.student_id, period, stop.stop_id, stop.latitude, stop.longitude)
        )
        infer_stop, stop_announcements, override = self._eta_options(student, period)
        await self._async_reported_completion(
            student, period, stop, now, completion_key, key, override
        )
        if completion_key in self._eta_reported or (
            infer_stop and completion_key in self._eta_arrived
        ):
            self._set_eta_done(student, reported=completion_key in self._eta_reported)
            return
        if stop_announcements and completion_key in self._eta_suppressed:
            student.eta_status = "passed"
        stamp = student.log_time
        reason = self._eta_position_reason(student, stop, now, moving=moving)
        if reason is not None:
            student.eta_estimate = Estimate(reason=reason)
            return
        point = Point(
            stamp,
            student.latitude,
            student.longitude,
            student.speed,
            street_name(student.address),
        )
        journey = self._eta_journeys.setdefault(key, Journey())
        if (
            journey.visit.last is not None
            and point.timestamp < journey.visit.last.timestamp
        ):
            student.eta_estimate = Estimate(reason="gps_out_of_order")
            return
        trips = await self.eta_history.async_trips(student, period, stop, now, override)
        result, stopped, passed = journey.observe(point, stop, trips, override)
        if infer_stop:
            student.stop_visit_inferred = False
            if stopped:
                await self._async_inferred_completion(
                    student,
                    period,
                    stop,
                    now,
                    journey,
                    override,
                    completion_key,
                    suppress=stop_announcements,
                )
                self._set_eta_done(student, len(trips))
                return
        if stop_announcements and (passed or completion_key in self._eta_suppressed):
            if completion_key not in self._eta_suppressed:
                self._eta_suppressed.add(completion_key)
                await self._async_save_eta_completion(now)
            student.eta_status = "passed"
            student.eta_estimate = Estimate(
                source="final_approach_passed",
                trips=len(trips),
                available_trips=len(trips),
                reason="passed",
            )
            return
        self._set_eta_estimate(student, result)

    def _set_eta_estimate(self, student: StudentData, result: Estimate) -> None:
        """Publish the estimate while withholding divergent voice predictions."""
        now = dt_util.now()
        student.eta_estimate = result
        student.stop_eta = result.minutes(now)
        if result.arrival is not None and student.stop_eta is None:
            student.eta_estimate = replace(result, reason="prediction_expired")
        if student.stop_eta is not None:
            student.eta_status = (
                "projecting" if result.reason == "projected" else "tracking"
            )
            student.eta_announcements_allowed = (
                student.stop_eta > 0
                and result.confidence not in ("divergent", "projected")
            )

    def _eta_position_reason(
        self,
        student: StudentData,
        stop: Stop,
        now: datetime,
        *,
        moving: bool,
    ) -> str | None:
        """Distinguish service, visibility, validity, and freshness failures."""
        stamp = student.log_time
        if not moving or (
            stamp is not None and not stop.start <= stamp.time() <= stop.end
        ):
            return "outside_service_window"
        if student.display_on_map is not True:
            return "gps_hidden"
        if (
            student.latent is not False
            or student.latitude is None
            or student.longitude is None
            or not valid_coordinates(student.latitude, student.longitude)
        ):
            return "gps_invalid"
        if stamp is None or not timedelta(0) <= now - stamp <= MAX_AGE:
            return "gps_stale"
        return None

    async def _async_inferred_completion(  # noqa: PLR0913, PLR0917
        self,
        student: StudentData,
        period: str,
        stop: Stop,
        now: datetime,
        journey: Journey,
        direction: float | None,
        completion_key: str,
        *,
        suppress: bool,
    ) -> None:
        """Archive an inferred approach and persist its independent completion latch."""
        trip = completed_trip(journey.recorded, stop, direction)
        if trip is not None:
            await self.eta_history.async_remember(
                student, period, stop, now, trip, direction
            )
        self._eta_arrived.add(completion_key)
        if suppress:
            self._eta_suppressed.add(completion_key)
        await self._async_save_eta_completion(now)

    async def _async_reported_completion(  # noqa: PLR0913, PLR0917
        self,
        student: StudentData,
        period: str,
        stop: Stop,
        now: datetime,
        completion_key: str,
        journey_key: tuple,
        direction: float | None,
    ) -> None:
        """Require a new report and recent approach, never yesterday's time alone."""
        if completion_key in self._eta_reported:
            return
        report = getattr(student, f"{period}_stop_arrival_time")
        changed = (
            completion_key in self._eta_reports
            and self._eta_reports[completion_key] != report
        )
        self._eta_reports[completion_key] = report
        if not changed or report is None:
            return
        arrival = datetime.combine(now.date(), report, now.tzinfo)
        journey = self._eta_journeys.get(journey_key)
        if journey is None or not timedelta(0) <= now - arrival <= MAX_GAP:
            return
        trip = reported_trip(journey.recorded, stop, arrival, direction)
        if trip is None:
            return
        self._eta_reported.add(completion_key)
        await self._async_save_eta_completion(now)
        await self.eta_history.async_remember(
            student, period, stop, now, trip, direction
        )

    def _get_time_of_day_id(self, check_time: time) -> str:
        """Get the time of day ID based on the given time."""
        if self._is_am(check_time):
            return TimeOfDay.AM
        if self._is_mid(check_time):
            return TimeOfDay.MID
        return TimeOfDay.PM

    def _adjust_time(self, base_time: time, delta_minutes: int) -> time:
        """Adjust a time by adding or subtracting minutes."""
        dummy_date = dt_util.now().date()
        dt_combined = datetime.combine(dummy_date, base_time)
        return (dt_combined + timedelta(minutes=delta_minutes)).time()

    def _get_start_time(self, stops: list[StudentStop]) -> time:
        earliest = min(stop.start_time for stop in stops)
        return self._adjust_time(earliest, -30)

    def _get_end_time(self, stops: list[StudentStop]) -> time:
        latest = max(stop.start_time for stop in stops)
        return self._adjust_time(latest, 30)

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
