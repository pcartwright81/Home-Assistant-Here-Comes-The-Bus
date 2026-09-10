"""Bounded route projection, contradictory GPS, and readable uncertainty."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, State

from custom_components.here_comes_the_bus.coordinator import HCBDataCoordinator
from custom_components.here_comes_the_bus.data import StudentData
from custom_components.here_comes_the_bus.eta import (
    MPH_TO_MPS,
    PROJECTION_LIMIT,
    Journey,
    Point,
    Trip,
    project_arrival,
    project_trip,
    recorder_points,
    route_position,
    street_name,
)
from custom_components.here_comes_the_bus.eta_archive import decode_trip, encode_trip
from custom_components.here_comes_the_bus.sensor import (
    ENTITY_DESCRIPTIONS,
    HCBSensor,
    estimated_arrival_details,
)

from .test_eta import BASE, STOP
from .test_eta_routes import shifted_trips


def projection_route() -> tuple[list[Point], list[Trip], Journey]:
    """Build an established route with reliable speed and a noisy GPS position."""
    points = [
        Point(
            BASE + timedelta(seconds=i * 10),
            35.02 - i * 0.0009,
            -80,
            10 / MPH_TO_MPS,
            "main street",
        )
        for i in range(12)
    ]
    trips = shifted_trips(points)
    journey = Journey()
    for point in points[:3]:
        journey.observe(point, STOP, trips)
    return points, trips, journey


def test_projection_bridges_gap_without_refreshing_confirmed_progress() -> None:
    """Resume estimates after a noisy fix, then recover strict route matching."""
    points, trips, journey = projection_route()
    anchors = dict(journey.progress)
    assert (
        journey.observe(replace(points[3], longitude=-80.002), STOP, trips)[0].arrival
        is None
    )
    for point in points[4:6]:
        result, stopped, passed = journey.observe(point, STOP, trips)
        assert result.reason == "projected"
        assert result.confidence == "projected"
        assert not stopped
        assert not passed
        assert journey.passage_start is None
        assert journey.progress == anchors
        assert result.valid_until == points[2].timestamp + PROJECTION_LIMIT
        assert result.earliest_arrival < result.arrival < result.latest_arrival
        assert journey.observe(point, STOP, trips)[0] == result
    assert result.minutes(result.valid_until + timedelta(seconds=1)) is None
    for point in points[6:9]:
        result = journey.observe(point, STOP, trips)[0]
    assert result.reason == "matched"


@pytest.mark.parametrize(
    "mode",
    [
        "missing_speed",
        "negative_speed",
        "nan_speed",
        "fast_speed",
        "expired",
        "no_position",
        "ambiguous",
        "off_route",
        "end_of_route",
        "reverse",
    ],
)
def test_projection_rejects_insufficient_or_conflicting_evidence(mode: str) -> None:
    """Reject bad speed, expired/ambiguous anchors, departures, and inferred arrival."""
    points, trips, journey = projection_route()
    trip = trips[0]
    anchor = journey.progress[trip.arrival]
    point = points[4]
    if mode.endswith("speed"):
        point = replace(
            point,
            speed={
                "missing_speed": None,
                "negative_speed": -1,
                "nan_speed": float("nan"),
                "fast_speed": 100,
            }[mode],
        )
    elif mode == "expired":
        point = replace(
            point, timestamp=anchor.timestamp + PROJECTION_LIMIT + timedelta(seconds=1)
        )
    elif mode == "no_position":
        anchor = replace(anchor, point=None)
    elif mode == "ambiguous":
        anchor = replace(
            anchor,
            matches=[anchor.matches[0], anchor.matches[0] + timedelta(minutes=2)],
        )
    elif mode == "off_route":
        point = replace(point, longitude=-81)
    elif mode == "end_of_route":
        point = replace(point, speed=80, timestamp=anchor.timestamp + PROJECTION_LIMIT)
        anchor = replace(anchor, point=replace(anchor.point, speed=80))
    elif mode == "reverse":
        # The projected endpoint is close, but the observed movement reversed.
        point = replace(
            points[2],
            timestamp=points[4].timestamp,
            latitude=points[2].latitude + 0.0002,
            speed=0,
        )
        anchor = replace(anchor, point=replace(anchor.point, speed=0))
    assert project_trip(trip, anchor, [point]) is None


def test_projection_requires_two_agreeing_routes_and_expires() -> None:
    """Projection never extends the match's lifetime or chooses divergent times."""
    points, trips, journey = projection_route()
    assert project_arrival(trips[:1], journey.progress, points[3:5]).arrival is None
    delayed = replace(trips[1], arrival=trips[1].arrival + timedelta(minutes=5))
    progress = {**journey.progress, delayed.arrival: journey.progress[trips[1].arrival]}
    assert project_arrival([trips[0], delayed], progress, points[3:5]).arrival is None
    for seconds in (30, 50, 61):
        point = replace(
            points[4],
            timestamp=points[2].timestamp + timedelta(seconds=seconds),
            speed=0,
        )
        # Parked GPS cannot keep an old projection alive indefinitely.
        result = project_arrival(trips, journey.progress, [point])
        assert (
            result.valid_until is None
            or result.valid_until <= points[2].timestamp + PROJECTION_LIMIT
        )
    assert result.arrival is None


def test_route_position_follows_bends_and_rejects_long_gaps() -> None:
    """Distance advances around the route rather than across its corner."""
    points = (
        Point(BASE, 35, -80),
        Point(BASE + timedelta(seconds=10), 35.001, -80),
        Point(BASE + timedelta(seconds=20), 35.001, -79.999),
    )
    trip = Trip(points, points[-1].timestamp)
    point = route_position(trip, BASE, 150)
    assert point.latitude == 35.001
    assert -80 < point.longitude < -79.999
    assert route_position(trip, BASE, 10000) is None
    long_gap = replace(
        trip,
        points=(points[0], replace(points[1], timestamp=BASE + timedelta(minutes=5))),
    )
    assert route_position(long_gap, BASE, 10) is None


def test_street_labels_are_optional_and_archives_remain_compatible() -> None:
    """Old archives remain readable; street labels omit house numbers and cities."""
    assert street_name("123 Main Street , Town") == "main street"
    assert street_name("125  MAIN Street, Town") == "main street"
    assert street_name(None) is None
    state = State(
        "device_tracker.bus",
        "123 Main Street, Town",
        {"latitude": 35, "longitude": -80},
        last_updated=BASE,
    )
    assert next(iter(recorder_points([state]))).street == "main street"
    _, trips, _ = projection_route()
    encoded = encode_trip(trips[0])
    assert decode_trip(encoded) == trips[0]
    legacy = {**encoded, "points": [p[:4] for p in encoded["points"]]}
    assert all(p.street is None for p in decode_trip(legacy).points)
    with pytest.raises(ValueError, match="Invalid archived point"):
        decode_trip({**encoded, "points": [["bad"]]})


async def test_projected_estimate_is_labelled_and_silences_announcements(
    hass: HomeAssistant,
) -> None:
    """A visible projected countdown cannot trigger normal arrival announcements."""
    points, trips, journey = projection_route()
    result = project_arrival(trips, journey.progress, points[3:5])
    coordinator = HCBDataCoordinator(hass, MagicMock(data={}, options={}))
    student = StudentData("Alice", "s")
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=points[4].timestamp,
    ):
        coordinator._set_eta_estimate(student, result)
    assert student.eta_status == "projecting"
    assert student.stop_eta is not None
    assert student.eta_announcements_allowed is False
    assert "Projecting from the last route match" in estimated_arrival_details(student)
    description = next(d for d in ENTITY_DESCRIPTIONS if d.key == "stop_eta")
    assert (
        HCBSensor(coordinator, description, student).extra_state_attributes[
            "valid_until"
        ]
        == result.valid_until.isoformat()
    )


def test_street_agreement_supports_but_cannot_override_gps() -> None:
    """A street label gives limited tolerance without accepting a distant road."""
    points, trips, journey = projection_route()
    trip = trips[0]
    anchor = journey.progress[trip.arrival]
    point = replace(points[4], longitude=-79.9995)
    assert project_trip(trip, anchor, [point]) is not None
    assert project_trip(trip, anchor, [replace(point, street=None)]) is None
    assert project_trip(trip, anchor, [replace(point, longitude=-79.998)]) is None


def test_stopped_projection_does_not_advance_route_progress() -> None:
    """A stationary bus retains its remaining route time instead of moving ahead."""
    _, trips, journey = projection_route()
    trip = trips[0]
    anchor = journey.progress[trip.arrival]
    anchor = replace(anchor, point=replace(anchor.point, speed=0))
    stopped = replace(anchor.point, timestamp=anchor.timestamp + timedelta(seconds=20))
    remaining, age = project_trip(trip, anchor, [stopped])
    assert remaining == pytest.approx(
        (trip.arrival - max(anchor.matches)).total_seconds()
    )
    assert age == 20
