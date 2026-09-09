"""Load only the bus's own recorder history off the event loop."""

from __future__ import annotations

from bisect import bisect_right
from calendar import SATURDAY
from contextlib import suppress
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import BUS, DOMAIN, LOGGER
from .eta import (
    MAX_GAP,
    Point,
    Stop,
    Trip,
    completed_trip,
    recorder_points,
    reported_trip,
)
from .eta_archive import Archive, archive_key

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import HomeAssistant

    from .data import StudentData

HISTORY_DAYS = 14
MAX_TRIPS = 10
QUERY_CHUNK = timedelta(minutes=15)


class History:
    """Cache reconstructed routes until the next local day or stop change."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize a per-entry cache."""
        self.hass = hass
        self.entry_id = entry_id
        self.cache: dict[tuple, list[Trip]] = {}
        self.day = None
        self.retry_after: dict[tuple, datetime] = {}
        self.archive = Archive(hass, entry_id)

    async def async_trips(
        self,
        student: StudentData,
        period: str,
        stop: Stop,
        now: datetime,
        direction: float | None = None,
    ) -> list[Trip]:
        """Resolve renamed entities through the registry and load bounded history."""
        if self.day != now.date():
            self.cache.clear()
            self.retry_after.clear()
            self.day = now.date()
        entity_id = self._entity_id("device_tracker", student, "location")
        if entity_id is None:
            return []
        saved_key = archive_key(student.student_id, period, stop, direction)
        try:
            await self.archive.async_load()
        except OSError:
            LOGGER.warning("Unable to read bus ETA archive", exc_info=True)
        archived = self.archive.trips(saved_key, now)
        if "recorder" not in self.hass.config.components:
            return archived
        # Recorder installs its database dependencies when it starts.
        from homeassistant.components.recorder import get_instance  # noqa: PLC0415
        from sqlalchemy.exc import SQLAlchemyError  # noqa: PLC0415

        log_id = self._entity_id("sensor", student, "log_time")
        speed_id = self._entity_id("sensor", student, "speed")
        arrival_id = self._entity_id("sensor", student, f"{period}_stop_arrival_time")
        key = (entity_id, period, stop, log_id, direction, speed_id, arrival_id)
        if now < self.retry_after.get(key, now):
            return archived
        if key not in self.cache:
            try:
                learned = await get_instance(self.hass).async_add_executor_job(
                    self._load,
                    entity_id,
                    stop,
                    now,
                    log_id,
                    direction,
                    speed_id,
                    arrival_id,
                )
                await self.archive.async_merge(saved_key, learned, now)
                self.cache[key] = self.archive.trips(saved_key, now)
            except (SQLAlchemyError, OSError):
                self.retry_after[key] = now + timedelta(minutes=15)
                LOGGER.warning(
                    "Unable to refresh bus ETA history; using available archived trips",
                    exc_info=True,
                )
                return self.archive.trips(saved_key, now)
            # A changed stop must never reuse the previous destination's model.
            for old in list(self.cache):
                if old[:2] == key[:2] and old != key:
                    del self.cache[old]
        return self.cache[key]

    def _entity_id(self, domain: str, student: StudentData, key: str) -> str | None:
        """Resolve this entry's entity, including user-assigned entity IDs."""
        registry = er.async_get(self.hass)
        unique_id = f"{student.first_name}_{BUS}_{key}".lower()
        entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
        entry = registry.async_get(entity_id) if entity_id else None
        return entity_id if entry and entry.config_entry_id == self.entry_id else None

    async def async_remember(  # noqa: PLR0913, PLR0917
        self,
        student: StudentData,
        period: str,
        stop: Stop,
        now: datetime,
        trip: Trip,
        direction: float | None = None,
    ) -> None:
        """Archive live completion without adding today's outcome to today's model."""
        try:
            await self.archive.async_merge(
                archive_key(student.student_id, period, stop, direction), [trip], now
            )
        except OSError:
            LOGGER.warning("Unable to save bus ETA trip", exc_info=True)

    def _load(  # noqa: PLR0913, PLR0917
        self,
        entity_id: str,
        stop: Stop,
        now: datetime,
        log_id: str | None = None,
        direction: float | None = None,
        speed_id: str | None = None,
        arrival_id: str | None = None,
    ) -> list[Trip]:
        """Stream completed windows into bounded trips on recorder's worker."""
        from homeassistant.components.recorder.history import (  # noqa: PLC0415
            get_significant_states,
        )

        trips = []
        for offset in range(1, HISTORY_DAYS + 1):
            day = now.date() - timedelta(days=offset)
            if day.weekday() >= SATURDAY:
                continue
            start = dt_util.as_utc(datetime.combine(day, stop.start, now.tzinfo))
            end = dt_util.as_utc(datetime.combine(day, stop.end, now.tzinfo))
            trip = None
            if arrival_id:
                states = get_significant_states(
                    self.hass,
                    start,
                    end,
                    [arrival_id],
                    include_start_time_state=False,
                    significant_changes_only=True,
                    minimal_response=False,
                    no_attributes=False,
                )
                arrival = reported_arrival(
                    states.get(arrival_id, []), dt_util.as_local(start)
                )
                if arrival is not None:
                    trip = reported_trip(
                        self._day_points(
                            entity_id,
                            start,
                            arrival + timedelta(microseconds=1),
                            log_id,
                            speed_id,
                        ),
                        stop,
                        arrival,
                        direction,
                    )
            if trip is None:
                trip = completed_trip(
                    self._day_points(entity_id, start, end, log_id, speed_id),
                    stop,
                    direction,
                )
            if trip is not None:
                trips.append(trip)
            if len(trips) == MAX_TRIPS:
                break
        return trips

    def _day_points(
        self,
        entity_id: str,
        start: datetime,
        end: datetime,
        log_id: str | None,
        speed_id: str | None,
    ) -> Iterable[Point]:
        """Keep only one small raw query in memory, including across legacy joins."""
        from homeassistant.components.recorder.history import (  # noqa: PLC0415
            get_significant_states,
        )

        last_location = []
        last_speed = []
        entity_ids = [item for item in (entity_id, log_id, speed_id) if item]
        while start < end:
            until = min(start + QUERY_CHUNK, end)
            states = get_significant_states(
                self.hass,
                start - timedelta(microseconds=1),
                until,
                entity_ids,
                include_start_time_state=False,
                significant_changes_only=False,
                minimal_response=False,
                no_attributes=False,
            )
            locations = last_location + states.get(entity_id, [])
            speeds = last_speed + (states.get(speed_id, []) if speed_id else [])
            last_location = locations[-1:]
            last_speed = speeds[-1:]
            if log_id and states.get(log_id):
                yield from recorder_points(
                    align_legacy_fixes(locations, states[log_id], speeds)
                )
            else:
                yield from recorder_points(states.get(entity_id, []))
            # Explicitly release raw states before fetching the next chunk.
            del states, locations, speeds
            start = until


def reported_arrival(states: list[State], day: datetime) -> datetime | None:
    """Accept one new arrival value recorded promptly on the same local day."""
    arrivals = set()
    for state in states:
        try:
            arrival = datetime.combine(
                day.date(), time.fromisoformat(state.state), day.tzinfo
            )
        except ValueError:
            continue
        if timedelta(0) <= state.last_changed - arrival <= MAX_GAP:
            arrivals.add(arrival)
    return next(iter(arrivals)) if len(arrivals) == 1 else None


def align_legacy_fixes(
    locations: list[State], logs: list[State], speeds: list[State] | None = None
) -> Iterable[State]:
    """
    Use recorded GPS log times to recover stationary fixes from older versions.

    Legacy trackers did not change attributes while stopped. The companion log-time
    sensor still recorded fresh fixes. Allow one second for platform callback order.
    """
    timestamps = [state.last_updated for state in locations]
    speeds = speeds or []
    speed_times = [state.last_updated for state in speeds]
    for log in logs:
        index = bisect_right(timestamps, log.last_updated + timedelta(seconds=1)) - 1
        if index < 0:
            continue
        location = locations[index]
        attributes = {**location.attributes, "eta_log_time": log.state}
        speed_index = (
            bisect_right(speed_times, log.last_updated + timedelta(seconds=1)) - 1
        )
        if speed_index >= 0 and attributes.get("eta_speed") is None:
            with suppress(ValueError):
                attributes["eta_speed"] = float(speeds[speed_index].state)
        yield State(
            location.entity_id,
            location.state,
            attributes,
            last_updated=max(location.last_updated, log.last_updated),
        )
