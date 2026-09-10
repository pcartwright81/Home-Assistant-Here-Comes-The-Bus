"""Persist bounded completed trips independently of recorder retention."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from itertools import pairwise
from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER
from .eta import MAX_POINTS, MIN_APPROACH_POINTS, Point, Stop, Trip, valid_coordinates

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

ARCHIVE_DAYS = 60
ARCHIVE_TRIPS = 30
IDENTITY_FIELDS = 8
LEGACY_POINT_FIELDS = 4
POINT_FIELDS = 5


def archive_key(
    student_id: str, period: str, stop: Stop, direction: float | None
) -> str:
    """Partition by student, service, destination, window, and direction."""
    return json.dumps(
        [
            student_id,
            period,
            stop.stop_id,
            stop.latitude,
            stop.longitude,
            stop.start.isoformat(),
            stop.end.isoformat(),
            direction,
        ]
    )


def encode_trip(trip: Trip) -> dict:
    """Serialize only the bounded route and its arrival provenance."""
    return {
        "arrival": trip.arrival.isoformat(),
        "direction": trip.direction,
        "source": trip.source,
        "points": [
            [p.timestamp.isoformat(), p.latitude, p.longitude, p.speed, p.street]
            for p in trip.points
        ],
    }


def decode_trip(value: dict) -> Trip:
    """Validate persisted data before using it for predictions."""
    arrival = dt_util.parse_datetime(value["arrival"])
    if any(
        len(row) not in (LEGACY_POINT_FIELDS, POINT_FIELDS) for row in value["points"]
    ):
        msg = "Invalid archived point"
        raise ValueError(msg)
    points = tuple(
        Point(
            dt_util.parse_datetime(row[0]),
            float(row[1]),
            float(row[2]),
            row[3],
            row[4] if len(row) == POINT_FIELDS and isinstance(row[4], str) else None,
        )
        for row in value["points"]
    )
    if (
        arrival is None
        or arrival.tzinfo is None
        or not MIN_APPROACH_POINTS <= len(points) <= MAX_POINTS
        or any(
            p.timestamp is None
            or p.timestamp.tzinfo is None
            or not valid_coordinates(p.latitude, p.longitude)
            for p in points
        )
        or any(a.timestamp >= b.timestamp for a, b in pairwise(points))
        or points[-1].timestamp > arrival
        or value["source"] not in ("inferred_stop", "reported_arrival")
        or (value["direction"] is not None and not math.isfinite(value["direction"]))
    ):
        msg = "Invalid archived trip"
        raise ValueError(msg)
    return Trip(points, arrival, value["direction"], value["source"])


def trip_quality(trip: Trip) -> tuple[datetime, int, int]:
    """Prefer a longer approach, then more samples and usable street labels."""
    return (
        trip.points[0].timestamp,
        -len(trip.points),
        -sum(point.street is not None for point in trip.points),
    )


class Archive:
    """Keep at most 30 trips per active destination for at most 60 days."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Use HA's versioned storage and atomic writes."""
        self.store = Store(hass, 1, f"{DOMAIN}.eta_trips.{entry_id}")
        self.records: dict[str, list[Trip]] = {}
        self.loaded = False

    async def async_load(self) -> None:
        """Skip malformed routes without disabling the integration."""
        if self.loaded:
            return
        saved = await self.store.async_load() or {}
        if not isinstance(saved, dict):
            LOGGER.warning("Ignoring malformed bus ETA archive")
            saved = {}
        for key, values in saved.items():
            try:
                identity = json.loads(key)
                if not isinstance(identity, list) or len(identity) != IDENTITY_FIELDS:
                    LOGGER.warning("Ignoring malformed bus ETA archive identity")
                    continue
                self.records[key] = [
                    decode_trip(value) for value in values[:ARCHIVE_TRIPS]
                ]
            except (KeyError, TypeError, ValueError):
                LOGGER.warning("Ignoring malformed bus ETA archive record")
        self.loaded = True

    def trips(self, key: str, now: datetime) -> list[Trip]:
        """Never train on today's trip, future records, or expired examples."""
        return [
            t
            for t in self.records.get(key, [])
            if now.date() - timedelta(days=ARCHIVE_DAYS)
            <= t.arrival.date()
            < now.date()
        ]

    async def async_merge(self, key: str, trips: list[Trip], now: datetime) -> None:
        """Prefer reported endpoints and retain one example per service day."""
        await self.async_load()
        records = dict(self.records)
        scope = json.loads(key)[:2]
        for old in list(records):
            if old != key and json.loads(old)[:2] == scope:
                del records[old]
        by_day = {}
        for trip in [*records.get(key, []), *trips]:
            day = trip.arrival.date()
            if now.date() - timedelta(days=ARCHIVE_DAYS) <= day <= now.date():
                previous = by_day.get(day)
                if (
                    previous is None
                    or (
                        trip.source == "reported_arrival"
                        and previous.source != "reported_arrival"
                    )
                    or (
                        trip.source == previous.source
                        and trip.arrival == previous.arrival
                        and trip_quality(trip) < trip_quality(previous)
                    )
                ):
                    by_day[day] = trip
        records[key] = sorted(by_day.values(), key=lambda t: t.arrival, reverse=True)[
            :ARCHIVE_TRIPS
        ]
        records = {
            k: [
                t
                for t in ts
                if now.date() - timedelta(days=ARCHIVE_DAYS)
                <= t.arrival.date()
                <= now.date()
            ]
            for k, ts in records.items()
        }
        records = {k: ts for k, ts in records.items() if ts}
        if records != self.records:
            await self.store.async_save(
                {
                    key: [encode_trip(trip) for trip in trips]
                    for key, trips in records.items()
                }
            )
            self.records = records
