"""Route sequences, quick stops, and independent voice-alert cutoff behavior."""

from dataclasses import replace
from datetime import UTC, time, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.here_comes_the_bus.const import (
    CONF_DIRECTIONS,
    CONF_INFER_STOP,
    CONF_STOP_ANNOUNCEMENTS,
    DOMAIN,
)
from custom_components.here_comes_the_bus.coordinator import HCBDataCoordinator
from custom_components.here_comes_the_bus.data import StudentData
from custom_components.here_comes_the_bus.eta import (
    Journey,
    Point,
    Trip,
    completed_trip,
    estimate,
    expected_direction,
)
from custom_components.here_comes_the_bus.eta_history import History, align_legacy_fixes

from .test_eta import BASE, STOP


def quick_points() -> list[Point]:
    """Capture one low-speed fix followed by departure, without a dwell requirement."""
    return [
        Point(BASE + timedelta(seconds=seconds), latitude, -80.0, speed)
        for seconds, latitude, speed in (
            (0, 35.003, 20),
            (20, 35.001, 10),
            (40, 35.0, 0),
            (60, 34.998, 20),
        )
    ]


def quick_trips() -> list[Trip]:
    """Return independent historical pickup trips."""
    return [
        completed_trip(
            [
                replace(p, timestamp=p.timestamp - timedelta(days=day))
                for p in quick_points()
            ],
            STOP,
        )
        for day in (1, 2)
    ]


def test_quick_stop_and_departure() -> None:
    """One stopped fix is sufficient evidence only once departure is observed."""
    points = quick_points()
    assert completed_trip(points[:-1], STOP) is None
    trip = completed_trip(points, STOP)
    assert trip.arrival == points[2].timestamp
    assert trip.direction == 180
    journey = Journey()
    for point in points[:-1]:
        assert journey.observe(point, STOP, quick_trips())[1] is False
    assert journey.observe(points[-1], STOP, quick_trips())[1] is True


def test_quick_stop_can_turn_after_departure() -> None:
    """Reproduce observed timing/geometry without retaining private coordinates."""
    # Two zero-speed fixes 25 seconds apart, then a 47-degree turn after the stop.
    points = [
        Point(BASE + timedelta(seconds=seconds), lat, lon, speed)
        for seconds, lat, lon, speed in (
            (0, 35.000133, -80.00119, 38),
            (14, 35.0, -80.0, 0),
            (39, 35.0000002, -79.9999998, 0),
            (56, 34.9994734, -79.9995105, 23),
        )
    ]
    points.insert(0, Point(BASE - timedelta(seconds=20), 35.00038, -80.004, 20))
    assert completed_trip(points, STOP).arrival == points[2].timestamp


def test_ambiguous_stops_need_override() -> None:
    """Two opposite-direction stops on a day cannot self-label a pickup."""
    southbound = quick_points()
    northbound = [
        replace(
            p, timestamp=p.timestamp + timedelta(minutes=2), latitude=70 - p.latitude
        )
        for p in quick_points()
    ]
    assert completed_trip(southbound + northbound, STOP) is None
    assert completed_trip(southbound + northbound, STOP, 180).direction == 180
    assert completed_trip(southbound + northbound, STOP, 0).direction == 0
    history = quick_trips()
    assert (
        expected_direction(history + [replace(t, direction=0) for t in history]) is None
    )
    assert expected_direction(history, 0) == 0


def test_ordered_path_disambiguates_repeated_street() -> None:
    """A distinct approach prefix resolves otherwise identical later positions."""
    # The same southbound street occurs twice, with a distinct west-side return.
    coordinates = [
        (35.003, -80.0),
        (35.002, -80.0),
        (35.001, -80.0),
        (35.0, -80.0),
        (35.003, -80.002),
        (35.003, -80.0),
        (35.002, -80.0),
        (35.001, -80.0),
        (35.0, -80.0),
    ]
    historical = tuple(
        Point(BASE + timedelta(seconds=40 * i), lat, lon)
        for i, (lat, lon) in enumerate(coordinates)
    )
    history = [
        Trip(
            tuple(
                replace(p, timestamp=p.timestamp - timedelta(days=day))
                for p in historical
            ),
            historical[-1].timestamp - timedelta(days=day),
            180,
        )
        for day in (1, 2)
    ]
    recent = list(historical[4:8])
    assert estimate(history, recent[-1], recent[-2]).arrival is None
    assert estimate(history, recent[-1], recent[-2], recent).arrival is not None


def test_gap_and_reversal_cannot_confirm_stop() -> None:
    """A stale candidate or a reversing vehicle is not a confirmed quick pickup."""
    points = quick_points()
    assert (
        completed_trip(
            [*points[:-1], replace(points[-1], timestamp=BASE + timedelta(minutes=10))],
            STOP,
        )
        is None
    )
    assert (
        completed_trip([*points[:-1], replace(points[-1], latitude=35.002)], STOP)
        is None
    )
    journey = Journey()
    journey.observe(points[0], STOP, quick_trips())
    assert (
        journey.observe(
            replace(points[1], timestamp=BASE + timedelta(minutes=10)),
            STOP,
            quick_trips(),
        )[0].arrival
        is None
    )


def shifted_trips(points: list[Point]) -> list[Trip]:
    """Use identical synthetic routes on two independent days."""
    return [
        Trip(
            tuple(
                replace(p, timestamp=p.timestamp - timedelta(days=day)) for p in points
            ),
            points[-1].timestamp - timedelta(days=day),
            180,
        )
        for day in (1, 2)
    ]


def test_journey_remembers_which_lap_after_prefix_leaves_window() -> None:
    """Keep earlier route evidence when the last four fixes alone are ambiguous."""
    street = [(35.01 - i * 0.001, -80.0) for i in range(9)]
    coordinates = [*street, (35.002, -80.002), (35.01, -80.002), *street]
    points = [
        Point(BASE + timedelta(seconds=30 * i), lat, lon)
        for i, (lat, lon) in enumerate(coordinates)
    ]
    history = shifted_trips(points)
    journey = Journey()
    # Starting on the repeated street cannot identify the lap.
    for point in points[:5]:
        assert journey.observe(point, STOP, history)[0].arrival is None
    # The west-side return identifies the second lap. Eventually that distinctive
    # prefix is no longer in the rolling window, but progress must survive.
    for point in points[9:]:
        result = journey.observe(point, STOP, history)[0]
    assert estimate(history, points[-1], points[-2], points[-4:]).arrival is None
    assert result.arrival == points[-1].timestamp
    assert len(journey.points) == 4
    assert len(journey.progress) == 2


def sparse_route() -> list[Point]:
    """Long GPS segments leave uncertainty at intervening road bends."""
    return [
        Point(BASE + timedelta(seconds=30 * i), 35.025 - i * 0.0045, -80.0)
        for i in range(6)
    ]


def test_progress_cannot_skip_a_future_loop() -> None:
    """A unique starting segment anchors the first pass through a repeated street."""
    street = [(35.01 - i * 0.001, -80.0) for i in range(9)]
    coordinates = [
        (35.012, -80.0),
        (35.011, -80.0),
        *street,
        (35.002, -80.002),
        (35.01, -80.002),
        *street,
    ]
    points = [
        Point(BASE + timedelta(seconds=30 * i), lat, lon)
        for i, (lat, lon) in enumerate(coordinates)
    ]
    history = shifted_trips(points)
    journey = Journey()
    for point in points[:11]:
        result = journey.observe(point, STOP, history)[0]
    assert estimate(history, points[10], points[9], points[7:11]).arrival is None
    assert result.arrival == points[-1].timestamp


def test_established_route_recovers_one_sparse_bend() -> None:
    """Bridge one 90-meter sampling discrepancy with three tight route matches."""
    points = sparse_route()
    history = shifted_trips(points)
    journey = Journey()
    for point in points[:3]:
        journey.observe(point, STOP, history)
    bend = replace(points[3], longitude=-80.001)
    assert estimate(history, bend, points[2], [*points[:3], bend]).arrival is None
    result = journey.observe(bend, STOP, history)[0]
    assert result.arrival == points[-1].timestamp
    # Repeated polling must not advance progress or refresh the GPS timestamp.
    assert journey.observe(bend, STOP, history)[0] == result
    assert journey.observe(points[4], STOP, history)[0].arrival == result.arrival


def bend_samples() -> tuple[list[Point], list[Trip]]:
    """Preserve observed bend timing and geometry at unrelated coordinates."""
    live = [
        Point(BASE + timedelta(seconds=seconds), lat, lon)
        for seconds, lat, lon in (
            (0, 35.0100151, -79.9999886),
            (18, 35.0100476, -79.9997240),
            (34, 35.0111461, -79.9990520),
            (81, 35.0139865, -79.9990162),
            (86, 35.0140921, -79.9987113),
            (116, 35.0144681, -79.9948887),
            (146, 35.0132096, -79.9921698),
        )
    ]
    historical = [
        Point(BASE + timedelta(seconds=seconds), lat, lon)
        for seconds, lat, lon in (
            (0, 35.0100000, -80.0000000),
            (17, 35.0100349, -79.9997266),
            (33, 35.0112011, -79.9990874),
            (62, 35.0134244, -80.0005357),
            (92, 35.0143193, -79.9980896),
            (122, 35.0143890, -79.9943694),
            (152, 35.0125397, -79.9921015),
        )
    ]
    return live, shifted_trips(historical)


def test_established_route_tracks_across_differently_sampled_bend() -> None:
    """A skipped bend fix must not drop a previously matched arrival estimate."""
    live, history = bend_samples()
    journey = Journey()
    journey.observe(live[0], STOP, history)
    for point in live[1:]:
        result = journey.observe(point, STOP, history)[0]
        assert result.reason == "matched"
        assert result.matching_trips == len(history)
        assert result.arrival >= point.timestamp
        assert journey.observe(point, STOP, history)[0] == result


def test_bend_heading_recovery_requires_established_progress() -> None:
    """Do not relax direction checks for a newly seen route."""
    live, history = bend_samples()
    assert estimate(history, live[3], live[2], live[:4]).arrival is None


@pytest.mark.parametrize("mode", ["expired", "one_trip", "reverse", "off_route"])
def test_bend_recovery_rejects_unsupported_matches(mode: str) -> None:
    """A bend cannot bypass history, freshness, direction, or distance checks."""
    live, history = bend_samples()
    if mode == "one_trip":
        history = history[:1]
    journey = Journey()
    for point in live[:3]:
        journey.observe(point, STOP, history)
    point = live[3]
    if mode == "expired":
        point = replace(point, timestamp=point.timestamp + timedelta(minutes=4))
    elif mode == "reverse":
        point = replace(point, latitude=live[1].latitude, longitude=live[1].longitude)
    elif mode == "off_route":
        point = replace(point, latitude=point.latitude + 0.003)
    assert journey.observe(point, STOP, history)[0].arrival is None


@pytest.mark.parametrize("mode", ["parallel", "detour", "dense", "one_trip"])
def test_recovery_still_requires_route_evidence(mode: str) -> None:
    """Do not widen dense routes, accept parallel streets, or use a single trip."""
    points = sparse_route()
    if mode == "dense":
        points = [replace(p, latitude=35.025 - i * 0.001) for i, p in enumerate(points)]
    history = shifted_trips(points)
    if mode == "one_trip":
        history = history[:1]
    journey = Journey()
    for point in points[:3]:
        journey.observe(point, STOP, history)
    offset = -80.002 if mode == "detour" else -80.001
    result = journey.observe(replace(points[3], longitude=offset), STOP, history)[0]
    if mode == "parallel":
        # One loose fix is tolerated, but following a parallel street is not.
        assert result.arrival is not None
        result = journey.observe(replace(points[4], longitude=offset), STOP, history)[0]
    assert result.arrival is None


def test_progress_expires_and_detour_can_rejoin() -> None:
    """Old anchors expire even when fresh off-route fixes continue arriving."""
    points = sparse_route()
    history = shifted_trips(points)
    journey = Journey()
    for point in points[:3]:
        journey.observe(point, STOP, history)
    for i in range(1, 8):
        point = replace(
            points[2],
            timestamp=points[2].timestamp + timedelta(seconds=30 * i),
            longitude=-81.0 + i * 0.001,
        )
        assert journey.observe(point, STOP, history)[0].arrival is None
    assert journey.progress == {}
    for point in points[:4]:
        result = journey.observe(
            replace(point, timestamp=point.timestamp + timedelta(minutes=5)),
            STOP,
            history,
        )[0]
    assert result.arrival == points[-1].timestamp + timedelta(minutes=5)
    # A GPS gap also clears progress and requires a new movement baseline.
    result = journey.observe(
        replace(points[4], timestamp=points[4].timestamp + timedelta(minutes=10)),
        STOP,
        history,
    )[0]
    assert result.arrival is None
    assert journey.progress == {}


async def test_pass_cutoff_is_not_pickup_and_survives_reload(
    hass: HomeAssistant,
) -> None:
    """Passing on the final approach silences voice alerts without claiming boarding."""
    hass.config.components.add("recorder")
    entry = MagicMock(
        data={"update_interval": 20},
        entry_id="cutoff",
        options={
            CONF_INFER_STOP: True,
            CONF_STOP_ANNOUNCEMENTS: True,
            CONF_DIRECTIONS: {"s": {"am": "S", "pm": "N"}},
        },
    )
    coordinator = HCBDataCoordinator(hass, entry)
    coordinator.eta_history.async_trips = AsyncMock(return_value=quick_trips())
    student = StudentData(
        "Alice",
        "s",
        eta_stops={"am": STOP},
        display_on_map=True,
        latent=False,
        speed=20,
    )

    async def update(instance: HCBDataCoordinator, point: Point) -> None:
        student.latitude, student.longitude, student.log_time = (
            point.latitude,
            point.longitude,
            point.timestamp,
        )
        with patch(
            "custom_components.here_comes_the_bus.coordinator.dt_util.now",
            return_value=point.timestamp,
        ):
            await instance._async_update_eta(student)

    # The opposite-side outbound pass must never silence the approaching pickup.
    for p in quick_points():
        await update(coordinator, replace(p, latitude=70 - p.latitude))
    assert student.eta_status != "passed"
    # Returning southbound passes the expected stop but the actual stop was missed.
    for p in quick_points():
        await update(
            coordinator, replace(p, timestamp=p.timestamp + timedelta(minutes=2))
        )
    assert student.eta_status == "passed"
    assert student.stop_visit_inferred is False
    assert student.eta_announcements_allowed is False
    assert student.stop_eta is None
    restarted = HCBDataCoordinator(hass, entry)
    restarted.eta_history.async_trips = AsyncMock(return_value=quick_trips())
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=BASE,
    ):
        await restarted._async_load_eta_completion()
    await update(
        restarted, replace(quick_points()[0], timestamp=BASE + timedelta(hours=1))
    )
    assert student.eta_status == "passed"
    assert not student.eta_announcements_allowed
    # The separate cutoff can be disabled without enabling pickup inference.
    entry.options = {CONF_INFER_STOP: False, CONF_STOP_ANNOUNCEMENTS: False}
    for p in quick_points()[:2]:
        await update(
            restarted, replace(p, timestamp=p.timestamp + timedelta(hours=1, minutes=1))
        )
    assert student.eta_status == "tracking"
    assert student.eta_announcements_allowed


def test_legacy_speed_alignment() -> None:
    """Existing speed sensors can label a quick stop without new tracker attributes."""
    points = quick_points()
    locations = [
        State(
            "device_tracker.bus",
            "road",
            {"latitude": p.latitude, "longitude": p.longitude},
            last_updated=p.timestamp,
        )
        for p in points
    ]
    logs = [
        State("sensor.log", p.timestamp.isoformat(), last_updated=p.timestamp)
        for p in points
    ]
    speeds = [
        State("sensor.speed", str(p.speed), last_updated=p.timestamp) for p in points
    ]
    result = list(align_legacy_fixes(locations, logs, speeds))
    assert result[2].attributes["eta_speed"] == 0
    speeds[2] = State("sensor.speed", "unknown", last_updated=points[2].timestamp)
    assert (
        "eta_speed"
        not in list(align_legacy_fixes(locations, logs, speeds))[2].attributes
    )


@pytest.mark.usefixtures("recorder_db_url")
@pytest.mark.freeze_time("2026-08-31T06:00:00+00:00")
async def test_legacy_quick_stop_across_recorder_chunk_boundary(
    hass: HomeAssistant, recorder_mock: Any, freezer: Any
) -> None:
    """Recover a brief legacy stop exactly at a chunk boundary from real recorder."""
    dt_util.set_default_time_zone(UTC)
    entry = MockConfigEntry(domain=DOMAIN, entry_id="boundary")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    entities = [
        registry.async_get_or_create(
            domain, DOMAIN, unique, config_entry=entry
        ).entity_id
        for domain, unique in (
            ("device_tracker", "alice_bus_location"),
            ("sensor", "alice_bus_log_time"),
            ("sensor", "alice_bus_speed"),
        )
    ]
    for day in (2, 1):
        for point in quick_points():
            stamp = point.timestamp - timedelta(days=day, seconds=40)
            freezer.move_to(stamp)
            hass.states.async_set(
                entities[0],
                "road",
                {"latitude": point.latitude, "longitude": point.longitude},
            )
            hass.states.async_set(entities[1], stamp.isoformat())
            hass.states.async_set(entities[2], str(point.speed))
            await hass.async_block_till_done()
    await recorder_mock.async_block_till_done()
    freezer.move_to(BASE)
    history = History(hass, "boundary")
    learned = await history.async_trips(StudentData("Alice", "s"), "am", STOP, BASE)
    assert len(learned) == 2
    assert all(trip.arrival.time() == time(7) for trip in learned)
