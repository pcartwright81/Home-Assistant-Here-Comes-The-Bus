"""Estimate stop arrivals from bounded, completed recorder trips."""

from __future__ import annotations

import math
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from itertools import pairwise
from statistics import median
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import State

ARRIVAL_RADIUS = 100
MATCH_RADIUS = 75
RECOVERY_RADIUS = 150
PROGRESS_RATE = 3
PROGRESS_SLACK = timedelta(seconds=30)
PROGRESS_BACKTRACK = timedelta(seconds=15)
MAX_SEGMENT = 750
MAX_AGE = timedelta(minutes=2)
PROJECTION_LIMIT = timedelta(minutes=1)
MPH_TO_MPS = 0.44704
MAX_PROJECTION_SPEED = 85
SEGMENT_MIDPOINT = 0.5
MAX_GAP = timedelta(minutes=3)
MAX_POINTS = 480
MIN_MOVEMENT = 20
MAX_HEADING_DIFFERENCE = 60
MIN_TRIPS = 2
MIN_APPROACH_POINTS = 2
STOP_DWELL = timedelta(seconds=30)
STOP_GAP = timedelta(seconds=45)
STOP_MOVEMENT = 15
MIN_STOP_FIXES = 3
MAX_STOP_SPEED = 1.0
LATITUDE_LIMIT = 90
LONGITUDE_LIMIT = 180
DIRECTION_CONSENSUS = 0.75
PATH_POINTS = 4
AMBIGUITY_SECONDS = 90
DEPARTURE_DISTANCE = 125
DIRECTION_DEGREES = {
    name: index * 45.0
    for index, name in enumerate(("N", "NE", "E", "SE", "S", "SW", "W", "NW"))
}


@dataclass(frozen=True, slots=True)
class Stop:
    """Identity and service window of the current destination."""

    stop_id: str
    latitude: float
    longitude: float
    start: time
    end: time


@dataclass(frozen=True, slots=True)
class Point:
    """A timestamped bus position."""

    timestamp: datetime
    latitude: float
    longitude: float
    speed: float | None = None
    street: str | None = None


@dataclass(frozen=True, slots=True)
class Trip:
    """A continuous approach ending at the destination."""

    points: tuple[Point, ...]
    arrival: datetime
    direction: float | None = None
    source: str = "inferred_stop"


@dataclass(frozen=True, slots=True)
class Estimate:
    """A countdown with an explicit source and supporting trip count."""

    arrival: datetime | None = None
    source: str = "unavailable"
    trips: int = 0
    available_trips: int = 0
    matching_trips: int = 0
    reason: str = "no_fresh_position"
    confidence: str = "unavailable"
    earliest_arrival: datetime | None = None
    latest_arrival: datetime | None = None
    valid_until: datetime | None = None

    def minutes(self, now: datetime) -> float | None:
        """Return remaining minutes, without displaying overdue predictions as zero."""
        if (
            self.arrival is None
            or self.arrival < now
            or (self.valid_until is not None and now > self.valid_until)
        ):
            return None
        return round((self.arrival - now).total_seconds() / 60, 1)


def distance(first: Point | Stop, second: Point | Stop) -> float:
    """Calculate great-circle distance in meters."""
    lat1, lat2 = math.radians(first.latitude), math.radians(second.latitude)
    delta = math.radians(second.longitude - first.longitude)
    value = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta / 2) ** 2
    )
    return 12_742_000 * math.asin(math.sqrt(min(1, max(0, value))))


def bearing(first: Point, second: Point) -> float:
    """Calculate travel direction from consecutive locations."""
    lat1, lat2 = math.radians(first.latitude), math.radians(second.latitude)
    delta = math.radians(second.longitude - first.longitude)
    return (
        math.degrees(
            math.atan2(
                math.sin(delta) * math.cos(lat2),
                math.cos(lat1) * math.sin(lat2)
                - math.sin(lat1) * math.cos(lat2) * math.cos(delta),
            )
        )
        % 360
    )


def street_name(address: str | None) -> str | None:
    """Use a street label as supporting evidence, omitting house and city."""
    match = re.match(r"^\d+\w*\s+([^,]+)", address or "")
    return " ".join(match[1].casefold().split()) if match else None


def recorder_points(states: Iterable[State]) -> Iterable[Point]:
    """Decode full tracker states; legacy states use their recorder timestamp."""
    previous = None
    for state in states:
        attrs = state.attributes
        if (
            state.state in ("unknown", "unavailable")
            or attrs.get("eta_gps_valid") is False
        ):
            continue
        try:
            latitude, longitude = float(attrs["latitude"]), float(attrs["longitude"])
            stamp = (
                dt_util.parse_datetime(attrs["eta_log_time"])
                if attrs.get("eta_log_time")
                else state.last_updated
            )
            if (
                stamp is None
                or stamp.tzinfo is None
                or not 0
                <= (state.last_updated - stamp).total_seconds()
                <= MAX_AGE.total_seconds()
            ):
                continue
            if not valid_coordinates(latitude, longitude):
                continue
        except (KeyError, TypeError, ValueError):
            continue
        speed = attrs.get("eta_speed")
        point = Point(
            dt_util.as_local(stamp),
            latitude,
            longitude,
            float(speed) if isinstance(speed, int | float) else None,
            street_name(state.state),
        )
        if previous is not None and point.timestamp <= previous:
            continue
        previous = point.timestamp
        yield point


def valid_coordinates(latitude: float, longitude: float) -> bool:
    """Reject invalid GPS coordinates and the service's empty (0, 0) location."""
    return (
        -LATITUDE_LIMIT <= latitude <= LATITUDE_LIMIT
        and -LONGITUDE_LIMIT <= longitude <= LONGITUDE_LIMIT
        and (latitude, longitude) != (0, 0)
    )


@dataclass(slots=True)
class StopVisit:
    """Recognize stopped fixes plus departure, or sustained stationary evidence."""

    last: Point | None = None
    movement: Point | None = None
    anchor: Point | None = None
    direction: float | None = None
    fixes: int = 0
    quick: Point | None = None
    quick_direction: float | None = None

    def observe(self, point: Point, stop: Stop) -> bool:
        """Recognize a stop without accumulating evidence from duplicate fixes."""
        if self.last is not None:
            if point.timestamp <= self.last.timestamp:
                return False
            if point.timestamp - self.last.timestamp > STOP_GAP:
                self.anchor = None
            if point.timestamp - self.last.timestamp > MAX_GAP:
                self.quick = None
                self.movement = None
                self.direction = None
        self.last = point
        if self.quick is not None and distance(point, self.quick) >= MIN_MOVEMENT:
            candidate = self.quick
            direction = self.quick_direction
            self.quick = None
            if (
                direction is not None
                and angle_difference(bearing(candidate, point), direction)
                <= MAX_HEADING_DIFFERENCE
            ):
                self.anchor = candidate
                self.direction = direction
                self.movement = point
                return True
        if self.movement is not None and distance(self.movement, point) >= MIN_MOVEMENT:
            self.direction = bearing(self.movement, point)
            self.movement = point
        elif self.movement is None:
            self.movement = point
        if distance(point, stop) > ARRIVAL_RADIUS or (
            point.speed is not None and point.speed > MAX_STOP_SPEED
        ):
            self.anchor = None
            self.fixes = 0
            return False
        if (
            point.speed is not None
            and 0 <= point.speed <= MAX_STOP_SPEED
            and self.direction is not None
            and self.quick is None
        ):
            self.quick = point
            self.quick_direction = self.direction
        if self.anchor is None or distance(self.anchor, point) > STOP_MOVEMENT:
            self.anchor = point
            self.fixes = 1
            return False
        self.fixes += 1
        return (
            self.direction is not None
            and self.fixes >= MIN_STOP_FIXES
            and point.timestamp - self.anchor.timestamp >= STOP_DWELL
        )


def completed_trip(
    points: Iterable[Point], stop: Stop, direction: float | None = None
) -> Trip | None:
    """Stream a day into one unambiguous stop approach with bounded memory."""
    approach: deque[Point] = deque(maxlen=MAX_POINTS)
    visit = StopVisit()
    selected = None
    in_visit = False
    for point in points:
        if not stop.start <= point.timestamp.time() <= stop.end or (
            visit.last is not None and point.timestamp <= visit.last.timestamp
        ):
            continue
        if approach and point.timestamp - approach[-1].timestamp > MAX_GAP:
            approach.clear()
        observed = visit.observe(point, stop)
        if (
            observed
            and not in_visit
            and len(approach) >= MIN_APPROACH_POINTS
            and distance(approach[0], stop) > ARRIVAL_RADIUS
        ):
            in_visit = True
            if (
                direction is None
                or angle_difference(visit.direction, direction)
                <= MAX_HEADING_DIFFERENCE
            ):
                if selected is not None:
                    # Multiple plausible stops on one day cannot label each other.
                    return None
                selected = Trip(
                    tuple(p for p in approach if p.timestamp <= visit.anchor.timestamp),
                    visit.anchor.timestamp,
                    visit.direction,
                )
        if distance(point, stop) > ARRIVAL_RADIUS:
            in_visit = False
        approach.append(point)
    return selected


def angle_difference(first: float, second: float) -> float:
    """Compare compass bearings across north."""
    return abs((first - second + 180) % 360 - 180)


def reported_trip(
    points: Iterable[Point],
    stop: Stop,
    arrival: datetime,
    direction: float | None = None,
) -> Trip | None:
    """Corroborate a reported arrival with a continuous, nearby GPS approach."""
    approach: deque[Point] = deque(maxlen=MAX_POINTS)
    for point in points:
        if point.timestamp.date() != arrival.date() or not (
            stop.start <= point.timestamp.time() <= stop.end
            and point.timestamp <= arrival
        ):
            continue
        if approach and point.timestamp - approach[-1].timestamp > MAX_GAP:
            approach.clear()
        if not approach or point.timestamp > approach[-1].timestamp:
            approach.append(point)
    if (
        len(approach) < MIN_APPROACH_POINTS
        or not stop.start <= arrival.time() <= stop.end
        or arrival - approach[-1].timestamp > MAX_GAP
        or distance(approach[0], stop) <= ARRIVAL_RADIUS
        or distance(approach[-1], stop) > MAX_SEGMENT
    ):
        return None
    last = approach[-1]
    previous = next(
        (p for p in reversed(approach) if distance(p, last) >= MIN_MOVEMENT), None
    )
    if previous is None or distance(previous, stop) <= distance(last, stop):
        return None
    heading = bearing(previous, last)
    if (
        direction is not None
        and angle_difference(heading, direction) > MAX_HEADING_DIFFERENCE
    ):
        return None
    return Trip(tuple(approach), arrival, heading, "reported_arrival")


def expected_direction(
    trips: list[Trip], override: float | None = None
) -> float | None:
    """Require a dominant historical approach, or use an explicit override."""
    if override is not None:
        return override
    directions = [trip.direction for trip in trips if trip.direction is not None]
    if len(directions) < MIN_TRIPS:
        return None
    cluster = max(
        (
            [
                other
                for other in directions
                if angle_difference(item, other) <= MAX_HEADING_DIFFERENCE
            ]
            for item in directions
        ),
        key=len,
    )
    if len(cluster) < MIN_TRIPS or len(cluster) / len(directions) < DIRECTION_CONSENSUS:
        return None
    return (
        math.degrees(
            math.atan2(
                sum(math.sin(math.radians(item)) for item in cluster),
                sum(math.cos(math.radians(item)) for item in cluster),
            )
        )
        % 360
    )


def compatible_stop(
    direction: float | None, trips: list[Trip], override: float | None = None
) -> bool:
    """Accept only the expected stop approach, not the opposite-side pass."""
    expected = expected_direction(trips, override)
    return (
        direction is not None
        and expected is not None
        and angle_difference(direction, expected) <= MAX_HEADING_DIFFERENCE
    )


def match_segment(point: Point, before: Point, after: Point) -> tuple[float, Point]:
    """Interpolate progress on a short historical segment without extrapolating."""
    longitude_scale = math.cos(math.radians(point.latitude))
    dx = (after.longitude - before.longitude) * longitude_scale
    dy = after.latitude - before.latitude
    px = (point.longitude - before.longitude) * longitude_scale
    py = point.latitude - before.latitude
    fraction = max(0.0, min(1.0, (px * dx + py * dy) / (dx * dx + dy * dy)))
    projected = Point(
        before.timestamp + (after.timestamp - before.timestamp) * fraction,
        before.latitude + (after.latitude - before.latitude) * fraction,
        before.longitude + (after.longitude - before.longitude) * fraction,
    )
    return distance(point, projected), projected


def match_path(
    trip: Trip, path: list[Point], *, recover: bool = False
) -> list[datetime]:
    """Match recent movement in temporal order, retaining ambiguous alternatives."""
    candidates: dict[datetime, tuple[int, Point]] = {}
    for index, point in enumerate(path):
        before_live, after_live = (
            (path[index - 1], point) if index else (point, path[1])
        )
        if distance(before_live, after_live) < MIN_MOVEMENT:
            return []
        direction = bearing(before_live, after_live)
        matches: dict[datetime, tuple[int, Point]] = {}
        for before, after in pairwise(trip.points):
            length = distance(before, after)
            if not MIN_MOVEMENT <= length <= MAX_SEGMENT:
                continue
            separation, projected = match_segment(point, before, after)
            heading_matches = (
                angle_difference(bearing(before, after), direction)
                <= MAX_HEADING_DIFFERENCE
            )
            # An established route may tolerate one sampling discrepancy. A
            # direction discrepancy must still be spatially close to the route.
            radius = (
                min(RECOVERY_RADIUS, max(MATCH_RADIUS, length / 4))
                if recover and heading_matches
                else MATCH_RADIUS
            )
            loose = int(separation > MATCH_RADIUS or not heading_matches)
            if separation > radius or loose > int(recover):
                continue
            # A live fix may skip a bend captured by historical GPS. Compare
            # travel between matched positions, not only the last short segment.
            # Keep temporal order and share the one-point recovery budget with
            # spatial tolerance; reversals and sustained mismatches still fail.
            prior = (
                min(
                    (
                        count
                        for previous_stamp, (count, previous) in candidates.items()
                        if previous_stamp <= projected.timestamp
                        and (
                            heading_matches
                            or (
                                MIN_MOVEMENT
                                <= distance(previous, projected)
                                <= MAX_SEGMENT
                                and angle_difference(
                                    bearing(previous, projected), direction
                                )
                                <= MAX_HEADING_DIFFERENCE
                            )
                        )
                    ),
                    default=2,
                )
                if index
                else (0 if heading_matches else 2)
            )
            if prior + loose <= int(recover):
                stamp = projected.timestamp
                cost = min(matches.get(stamp, (2, projected))[0], prior + loose)
                matches[stamp] = (cost, projected)
        candidates = matches
        if not candidates:
            break
    return list(candidates)


@dataclass(slots=True)
class Progress:
    """Keep plausible historical positions across the rolling live path."""

    timestamp: datetime
    matches: list[datetime]
    point: Point | None = None

    def constrain(self, matches: list[datetime], now: datetime) -> list[datetime]:
        """Reject jumps to another lap while allowing different driving speeds."""
        advance = (now - self.timestamp) * PROGRESS_RATE + PROGRESS_SLACK
        return [
            stamp
            for stamp in matches
            if any(
                -PROGRESS_BACKTRACK <= stamp - previous <= advance
                for previous in self.matches
            )
        ]


def estimate(
    trips: list[Trip],
    point: Point | None,
    previous: Point | None,
    recent: list[Point] | None = None,
    progress: dict[datetime, Progress] | None = None,
) -> Estimate:
    """Match ordered recent movement and reject ambiguous progress on loops."""
    if (
        point is None
        or previous is None
        or not timedelta(0) < point.timestamp - previous.timestamp <= MAX_GAP
    ):
        return Estimate(
            trips=len(trips), available_trips=len(trips), reason="insufficient_movement"
        )
    path = recent if recent is not None else [previous, point]
    candidates = []
    ambiguous = False
    for trip in trips:
        anchor = progress.get(trip.arrival) if progress is not None else None
        if anchor is not None and point.timestamp - anchor.timestamp > MAX_GAP:
            del progress[trip.arrival]
            anchor = None
        # Polling the same GPS fix cannot accumulate slack and creep along a loop.
        matches = (
            anchor.matches
            if anchor is not None and point.timestamp == anchor.timestamp
            else match_path(trip, path)
        )
        if anchor is not None:
            matches = anchor.constrain(matches, point.timestamp)
            if (
                not matches
                and (max(anchor.matches) - min(anchor.matches)).total_seconds()
                <= AMBIGUITY_SECONDS
                and len(path) == PATH_POINTS
            ):
                matches = anchor.constrain(
                    match_path(trip, path, recover=True), point.timestamp
                )
        if matches and progress is not None:
            progress[trip.arrival] = Progress(point.timestamp, matches, point)
        if (
            matches
            and (max(matches) - min(matches)).total_seconds() <= AMBIGUITY_SECONDS
        ):
            candidates.append((trip.arrival - max(matches)).total_seconds())
        elif matches:
            ambiguous = True
    if len(candidates) >= MIN_TRIPS:
        return Estimate(
            point.timestamp + timedelta(seconds=median(candidates)),
            "historical_position",
            len(candidates),
            available_trips=len(trips),
            matching_trips=len(candidates),
            reason="matched",
            confidence=(
                "divergent"
                if max(candidates) - min(candidates) > AMBIGUITY_SECONDS
                else "limited"
                if len(candidates) == MIN_TRIPS
                else "consistent"
            ),
            earliest_arrival=point.timestamp + timedelta(seconds=min(candidates)),
            latest_arrival=point.timestamp + timedelta(seconds=max(candidates)),
        )
    return Estimate(
        trips=len(trips),
        available_trips=len(trips),
        matching_trips=len(candidates),
        reason="insufficient_history"
        if len(trips) < MIN_TRIPS
        else "ambiguous_route"
        if ambiguous
        else "insufficient_matches",
    )


def route_position(trip: Trip, stamp: datetime, meters: float) -> Point | None:
    """Advance along historical segments instead of cutting across a loop."""
    for before, after in pairwise(trip.points):
        if after.timestamp <= stamp:
            continue
        fraction = max(
            0.0, (stamp - before.timestamp) / (after.timestamp - before.timestamp)
        )
        start = Point(
            max(stamp, before.timestamp),
            before.latitude + fraction * (after.latitude - before.latitude),
            before.longitude + fraction * (after.longitude - before.longitude),
            street=before.street,
        )
        length = distance(start, after)
        if length > MAX_SEGMENT or after.timestamp - before.timestamp > MAX_GAP:
            return None
        if meters <= length and length > 0:
            fraction = meters / length
            return Point(
                start.timestamp + (after.timestamp - start.timestamp) * fraction,
                start.latitude + fraction * (after.latitude - start.latitude),
                start.longitude + fraction * (after.longitude - start.longitude),
                street=after.street if fraction > SEGMENT_MIDPOINT else before.street,
            )
        meters -= length
    return None


def project_trip(
    trip: Trip, anchor: Progress, samples: list[Point]
) -> tuple[float, float] | None:
    """Project only a recent, unambiguous match corroborated by current GPS."""
    point = samples[-1]
    age = point.timestamp - anchor.timestamp
    if (
        anchor.point is None
        or not timedelta(0) < age <= PROJECTION_LIMIT
        or (max(anchor.matches) - min(anchor.matches)).total_seconds()
        > AMBIGUITY_SECONDS
    ):
        return None
    path = [anchor.point, *(p for p in samples if p.timestamp > anchor.timestamp)]
    if any(
        not isinstance(p.speed, int | float)
        or not math.isfinite(p.speed)
        or not 0 <= p.speed <= MAX_PROJECTION_SPEED
        for p in path
    ):
        return None
    meters = sum(
        (a.speed + b.speed)
        / 2
        * MPH_TO_MPS
        * (b.timestamp - a.timestamp).total_seconds()
        for a, b in pairwise(path)
    )
    projected = route_position(trip, max(anchor.matches), meters)
    origin = route_position(trip, max(anchor.matches), 0)
    if projected is None or origin is None or projected.timestamp >= trip.arrival:
        return None
    same_street = point.street is not None and point.street == projected.street
    radius = min(
        MATCH_RADIUS, 25 + age.total_seconds() / 2 + (15 if same_street else 0)
    )
    if distance(point, projected) > radius:
        return None
    if distance(anchor.point, point) >= MIN_MOVEMENT and (
        distance(origin, projected) < MIN_MOVEMENT
        or angle_difference(bearing(anchor.point, point), bearing(origin, projected))
        > MAX_HEADING_DIFFERENCE
    ):
        return None
    return (trip.arrival - projected.timestamp).total_seconds(), age.total_seconds()


def project_arrival(
    trips: list[Trip], progress: dict[datetime, Progress], samples: list[Point]
) -> Estimate:
    """Bridge a short route-match gap without refreshing the confirmed anchors."""
    candidates = [
        candidate
        for trip in trips
        if (anchor := progress.get(trip.arrival)) is not None
        and (candidate := project_trip(trip, anchor, samples)) is not None
    ]
    if len(candidates) < MIN_TRIPS:
        return Estimate(reason="insufficient_matches")
    remaining, ages = zip(*candidates, strict=True)
    if max(remaining) - min(remaining) > AMBIGUITY_SECONDS:
        return Estimate(reason="ambiguous_route")
    point = samples[-1]
    uncertainty = max(ages) / 2 + 10
    return Estimate(
        arrival=point.timestamp + timedelta(seconds=median(remaining)),
        source="historical_projection",
        trips=len(candidates),
        available_trips=len(trips),
        matching_trips=0,
        reason="projected",
        confidence="projected",
        earliest_arrival=point.timestamp
        + timedelta(seconds=max(0, min(remaining) - uncertainty)),
        latest_arrival=point.timestamp
        + timedelta(seconds=max(remaining) + uncertainty),
        valid_until=point.timestamp + PROJECTION_LIMIT - timedelta(seconds=max(ages)),
    )


@dataclass(slots=True)
class Journey:
    """Keep a small recent path and distinguish completion from passing the stop."""

    points: list[Point] = field(default_factory=list)
    visit: StopVisit = field(default_factory=StopVisit)
    passage_start: Point | None = None
    progress: dict[datetime, Progress] = field(default_factory=dict)
    recorded: deque[Point] = field(default_factory=lambda: deque(maxlen=MAX_POINTS))

    def observe(
        self, point: Point, stop: Stop, trips: list[Trip], override: float | None = None
    ) -> tuple[Estimate, bool, bool]:
        """Return the ETA, a supported stop visit, and a final-approach passage."""
        if self.visit.last is not None and (
            point.timestamp - self.visit.last.timestamp > MAX_GAP
        ):
            self.points.clear()
            self.progress.clear()
            self.passage_start = None
            self.recorded.clear()
        if not self.recorded or point.timestamp > self.recorded[-1].timestamp:
            self.recorded.append(point)
        stopped = self.visit.observe(point, stop)
        if self.points and distance(self.points[-1], point) < MIN_MOVEMENT:
            path = [*self.points[:-1], point]
        else:
            path = [*self.points, point][-PATH_POINTS:]
        self.points = path
        previous = path[-2] if len(path) >= MIN_APPROACH_POINTS else None
        self.progress = {
            trip.arrival: self.progress[trip.arrival]
            for trip in trips
            if trip.arrival in self.progress
        }
        result = estimate(trips, point, previous, path, self.progress)
        if result.reason == "insufficient_matches":
            projected = project_arrival(trips, self.progress, list(self.recorded))
            if projected.arrival is not None:
                result = projected
        direction = expected_direction(trips, override)
        passed = False
        if direction is not None:
            if self.passage_start is not None:
                passed = passed_stop(self.passage_start, point, stop, direction)
            # History identifies the final approach; an override can bootstrap it.
            near_final = (
                result.reason == "matched"
                and result.arrival is not None
                and timedelta(0)
                <= result.arrival - point.timestamp
                <= timedelta(minutes=2)
            )
            if (near_final or override is not None) and -MAX_SEGMENT <= along_stop(
                point, stop, direction
            ) <= -MIN_MOVEMENT:
                self.passage_start = point
        return (
            result,
            stopped and compatible_stop(self.visit.direction, trips, override),
            passed,
        )


def along_stop(point: Point, stop: Stop, direction: float) -> float:
    """Project a position onto the expected approach axis in meters."""
    return distance(stop, point) * math.cos(
        math.radians(
            bearing(Point(point.timestamp, stop.latitude, stop.longitude), point)
            - direction
        )
    )


def passed_stop(before: Point, after: Point, stop: Stop, direction: float) -> bool:
    """Recognize crossing the stop in the final direction without claiming a stop."""
    if (
        not timedelta(0) < after.timestamp - before.timestamp <= MAX_GAP
        or not MIN_MOVEMENT <= distance(before, after) <= MAX_SEGMENT
    ):
        return False
    separation, _ = match_segment(
        Point(after.timestamp, stop.latitude, stop.longitude), before, after
    )
    return (
        along_stop(before, stop, direction) <= -MIN_MOVEMENT
        and along_stop(after, stop, direction) >= DEPARTURE_DISTANCE
        and separation <= MATCH_RADIUS
        and angle_difference(bearing(before, after), direction)
        <= MAX_HEADING_DIFFERENCE
    )
