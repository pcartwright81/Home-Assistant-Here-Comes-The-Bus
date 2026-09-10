"""Exercise historical ETA behavior, including missing data and detours."""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.here_comes_the_bus.binary_sensor import (
    ENTITY_DESCRIPTIONS as BINARY_DESCRIPTIONS,
)
from custom_components.here_comes_the_bus.binary_sensor import (
    HCBBinarySensor,
)
from custom_components.here_comes_the_bus.const import CONF_INFER_STOP, DOMAIN
from custom_components.here_comes_the_bus.coordinator import (
    HCBDataCoordinator,
    TimeOfDay,
)
from custom_components.here_comes_the_bus.data import StudentData
from custom_components.here_comes_the_bus.device_tracker import (
    DEVICE_TRACKERS,
    HCBTracker,
)
from custom_components.here_comes_the_bus.eta import (
    MAX_POINTS,
    Estimate,
    Point,
    Stop,
    Trip,
    completed_trip,
    estimate,
    recorder_points,
    valid_coordinates,
)
from custom_components.here_comes_the_bus.eta_history import History, align_legacy_fixes
from custom_components.here_comes_the_bus.sensor import ENTITY_DESCRIPTIONS, HCBSensor

BASE = datetime(2026, 9, 2, 7, tzinfo=UTC)
STOP = Stop("stop1", 35.0, -80.0, time(6), time(9))


def approach(day: datetime = BASE) -> list[Point]:
    """Return a southbound approach, sampled every minute."""
    points = [
        Point(day + timedelta(minutes=i), 35.008 - i * 0.002, -80.0) for i in range(5)
    ]
    return points + [
        replace(points[-1], timestamp=points[-1].timestamp + timedelta(seconds=seconds))
        for seconds in (20, 40)
    ]


def trips() -> list[Trip]:
    """Build two independent completed school days."""
    return [completed_trip(approach(BASE - timedelta(days=i)), STOP) for i in (1, 2)]


def state(point: Point, **attrs: object) -> State:
    """Build a recorded tracker update."""
    return State(
        "device_tracker.renamed",
        "address",
        {"latitude": point.latitude, "longitude": point.longitude, **attrs},
        last_updated=point.timestamp,
    )


def test_prediction_and_countdown() -> None:
    """Match historical progress and count down even without a new GPS fix."""
    before, current = approach()[1:3]
    result = estimate(trips(), current, before)
    assert result.source == "historical_position"
    assert result.trips == 2
    assert result.minutes(current.timestamp) == 2
    assert result.minutes(current.timestamp + timedelta(seconds=30)) == 1.5
    assert result.minutes(current.timestamp + timedelta(minutes=3)) is None
    assert Estimate().minutes(BASE) is None


@pytest.mark.parametrize(
    "mode",
    [
        "no_history",
        "one_trip",
        "detour",
        "reverse",
        "stationary",
        "gap",
        "no_fix",
        "no_direction",
    ],
)
def test_uncertain_positions_are_unknown(mode: str) -> None:
    """Never substitute a timetable or incompatible route for missing evidence."""
    before, current = approach()[1:3]
    history = trips()
    if mode == "no_history":
        history = []
    elif mode == "one_trip":
        history = history[:1]
    elif mode == "detour":
        current = replace(current, longitude=-81)
    elif mode == "reverse":
        before = replace(before, latitude=35.002)
    elif mode == "stationary":
        before = replace(before, latitude=current.latitude)
    elif mode == "gap":
        before = replace(before, timestamp=before.timestamp - timedelta(hours=1))
    elif mode == "no_fix":
        current = None
    elif mode == "no_direction":
        before = None
    assert estimate(history, current, before).minutes(BASE) is None


def test_historical_stationary_samples_and_incomplete_routes() -> None:
    """Do not infer direction while parked, or learn across missing data."""
    points = approach()
    parked = replace(points[1], latitude=points[0].latitude)
    history = [Trip((points[0], parked), points[-1].timestamp)] * 2
    assert estimate(history, points[2], points[1]).arrival is None
    assert (
        completed_trip(
            [points[0], replace(points[-1], timestamp=BASE + timedelta(minutes=30))],
            STOP,
        )
        is None
    )
    assert completed_trip([points[-1]], STOP) is None
    assert completed_trip(points[:5], STOP) is None
    assert (
        completed_trip(
            [replace(points[0], timestamp=BASE.replace(hour=5)), *points], STOP
        )
        is not None
    )
    assert completed_trip(points[:-1], STOP) is None
    dense = [
        Point(BASE + timedelta(seconds=i), 35.01, -80) for i in range(MAX_POINTS + 1)
    ]
    dense += [
        Point(dense[-1].timestamp + timedelta(seconds=seconds), 35, -80)
        for seconds in (1, 21, 41)
    ]
    assert len(completed_trip(dense, STOP).points) == MAX_POINTS - 1


def test_recorder_decoding() -> None:
    """Use legacy timestamps but reject invalid, stale, or unordered fixes."""
    point = approach()[0]
    good = state(point)
    cases = [
        State(good.entity_id, "unknown", {}, last_updated=BASE),
        state(point, eta_gps_valid=False),
        State(good.entity_id, "address", {}, last_updated=BASE),
        state(point, latitude="bad"),
        state(point, latitude=float("nan")),
        state(point, eta_log_time="bad"),
        state(point, eta_log_time="2026-09-02T07:00:00"),
        state(point, eta_log_time=(BASE - timedelta(hours=1)).isoformat()),
        good,
        good,
        state(approach()[1], eta_log_time=approach()[1].timestamp.isoformat()),
    ]
    assert list(recorder_points(cases)) == [
        replace(p, timestamp=dt_util.as_local(p.timestamp)) for p in approach()[:2]
    ]
    assert valid_coordinates(0, 30)
    assert not valid_coordinates(0, 0)


async def test_history_registry_cache_and_failures(hass: HomeAssistant) -> None:
    """Honor recorder availability, renames, entry ownership and cache invalidation."""
    history = History(hass, "entry")
    student = StudentData("Alice", "s")
    assert await history.async_trips(student, "am", STOP, BASE) == []
    hass.config.components.add("recorder")
    config_entry = MockConfigEntry(domain=DOMAIN, entry_id="entry")
    config_entry.add_to_hass(hass)
    assert await history.async_trips(student, "am", STOP, BASE) == []
    registry = er.async_get(hass)
    tracker = registry.async_get_or_create(
        "device_tracker", DOMAIN, "alice_bus_location", config_entry=config_entry
    )
    registry.async_update_entity(
        tracker.entity_id, new_entity_id="device_tracker.renamed"
    )
    worker = AsyncMock(return_value=trips())
    with patch(
        "homeassistant.components.recorder.get_instance",
        return_value=MagicMock(async_add_executor_job=worker),
    ):
        assert len(await history.async_trips(student, "am", STOP, BASE)) == 2
        await history.async_trips(student, "am", STOP, BASE)
        assert worker.await_count == 1
        assert worker.call_args.args[1] == "device_tracker.renamed"
        changed = replace(STOP, stop_id="new", latitude=36)
        await history.async_trips(student, "am", changed, BASE)
        assert len(history.cache) == 1
        await history.async_trips(student, "am", changed, BASE + timedelta(days=1))
        assert worker.await_count == 3
        worker.side_effect = OSError("database unavailable")
        assert await history.async_trips(student, "pm", STOP, BASE) == []
        assert (
            await history.async_trips(student, "pm", STOP, BASE + timedelta(minutes=1))
            == []
        )
    foreign = History(hass, "different-entry")
    assert await foreign.async_trips(student, "am", STOP, BASE) == []


def test_history_load_filters_and_bounds(hass: HomeAssistant) -> None:
    """Read only complete past windows, preserving GPS-only attribute changes."""
    dt_util.set_default_time_zone(UTC)
    history = History(hass, "entry")

    def read(
        _hass: HomeAssistant,
        start: datetime,
        end: datetime,
        entity_ids: list[str],
        **kwargs: object,
    ) -> dict:
        assert entity_ids == ["device_tracker.renamed"]
        assert end < BASE
        assert kwargs == {
            "include_start_time_state": False,
            "significant_changes_only": False,
            "minimal_response": False,
            "no_attributes": False,
        }
        day = end.replace(hour=7, minute=0, second=0, microsecond=0)
        return {
            entity_ids[0]: [
                state(p) for p in approach(day) if start < p.timestamp < end
            ]
        }

    with patch(
        "homeassistant.components.recorder.history.get_significant_states",
        side_effect=read,
    ) as query:
        assert len(history._load("device_tracker.renamed", STOP, BASE)) == 10
        assert query.call_count == 120
        assert all(
            call.args[2] - call.args[1] <= timedelta(minutes=15, microseconds=1)
            for call in query.call_args_list
        )
    with patch(
        "homeassistant.components.recorder.history.get_significant_states",
        return_value={},
    ):
        assert history._load("device_tracker.renamed", STOP, BASE) == []


async def test_coordinator_lifecycle(hass: HomeAssistant) -> None:
    """Exercise predictions, duplicate fixes, detours, arrivals, and new cycles."""
    hass.config.components.add("recorder")
    coordinator = HCBDataCoordinator(
        hass,
        MagicMock(
            data={"update_interval": 20},
            entry_id="entry",
            options={CONF_INFER_STOP: True},
        ),
    )
    coordinator.eta_history.async_trips = AsyncMock(return_value=trips())
    student = StudentData(
        "Alice", "s", eta_stops={"am": STOP}, display_on_map=True, latent=False
    )

    async def update(point: Point, now: datetime | None = None) -> None:
        student.latitude, student.longitude, student.log_time = (
            point.latitude,
            point.longitude,
            point.timestamp,
        )
        with patch(
            "custom_components.here_comes_the_bus.coordinator.dt_util.now",
            return_value=now or point.timestamp,
        ):
            await coordinator._async_update_eta(student)

    points = approach()
    await update(points[1])
    assert student.stop_eta is None
    await update(points[2])
    assert student.stop_eta == 2
    await update(points[2], points[2].timestamp + timedelta(seconds=30))
    assert student.stop_eta == 1.5
    await update(points[1], points[2].timestamp)
    assert student.stop_eta is None
    await update(replace(points[3], longitude=-81))
    assert student.stop_eta is None
    # A changed stop discards the live progress baseline as well as history.
    student.eta_stops["am"] = replace(STOP, stop_id="new")
    await update(points[2])
    assert student.stop_eta is None
    await update(points[3])
    await update(points[4])
    assert student.stop_visit_inferred is False
    await update(points[5])
    await update(points[6])
    assert student.stop_eta == 0
    assert student.eta_estimate.source == "inferred_stop"
    assert student.eta_status == "done"
    await update(points[4])
    assert student.stop_visit_inferred is True
    assert student.stop_eta == 0
    await update(points[1], BASE.replace(hour=10))
    assert student.eta_status == "done"
    await update(replace(points[1], timestamp=BASE + timedelta(days=1)))
    assert student.stop_eta is None
    student.display_on_map = False
    await update(points[1])
    assert student.stop_eta is None
    student.display_on_map = True
    await update(points[1], points[1].timestamp + timedelta(minutes=10))
    assert student.stop_eta is None


def test_destination_and_entity_attributes(hass: HomeAssistant) -> None:
    """Capture stop identities and expose compact sensor and tracker diagnostics."""
    coordinator = HCBDataCoordinator(
        hass,
        MagicMock(
            data={"update_interval": 20},
            entry_id="entry",
            options={CONF_INFER_STOP: True},
        ),
    )
    student = StudentData("Alice", "s")
    destination = MagicMock(
        stop_type="School",
        time_of_day_id=TimeOfDay.AM,
        latitude=35.0,
        longitude=-80.0,
        stop_id="stop1",
        start_time=time(7),
    )
    coordinator._update_eta_stop(student, [destination])
    assert student.eta_stops == {}
    destination.stop_type = "Stop"
    coordinator._update_eta_stop(student, [destination])
    assert student.eta_stops["am"].stop_id == "stop1"
    description = next(item for item in ENTITY_DESCRIPTIONS if item.key == "stop_eta")
    sensor = HCBSensor(coordinator, description, student)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes["source"] == "unavailable"
    student.eta_estimate = Estimate(BASE, "historical_position", 2)
    assert sensor.extra_state_attributes["estimated_arrival"] == BASE.isoformat()
    ordinary = HCBSensor(coordinator, ENTITY_DESCRIPTIONS[0], student)
    assert ordinary.extra_state_attributes is None
    tracker = HCBTracker(coordinator, student, DEVICE_TRACKERS[0])
    assert tracker.extra_state_attributes["eta_log_time"] is None
    student.log_time = BASE
    student.display_on_map = True
    student.latent = False
    assert tracker.extra_state_attributes == {
        "eta_log_time": BASE.isoformat(),
        "eta_gps_valid": True,
        "eta_speed": None,
    }


async def test_stop_inference_requires_evidence_and_survives_restart(
    hass: HomeAssistant,
) -> None:
    """Preserve completion across reloads and reset it for the next trip."""
    hass.config.components.add("recorder")
    entry = MagicMock(
        data={"update_interval": 20}, entry_id="entry", options={CONF_INFER_STOP: True}
    )
    coordinator = HCBDataCoordinator(hass, entry)
    coordinator.eta_history.async_trips = AsyncMock(return_value=trips())
    student = StudentData(
        "Alice", "s", eta_stops={"am": STOP}, display_on_map=True, latent=False, speed=0
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

    for point in approach()[:5]:
        await update(coordinator, point)
    assert student.eta_status != "done"
    # Duplicate fixes must never accumulate stationary time.
    for _ in range(3):
        await update(coordinator, approach()[4])
    assert student.eta_status != "done"
    for point in approach()[5:]:
        await update(coordinator, point)
    assert student.eta_status == "done"
    restarted = HCBDataCoordinator(hass, entry)
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=BASE,
    ):
        await restarted._async_load_eta_completion()
    await update(restarted, replace(approach()[0], timestamp=BASE + timedelta(hours=1)))
    assert student.eta_status == "done"
    # PM is an independent service cycle, even when it uses the same location.
    student.eta_stops["pm"] = replace(STOP, start=time(14), end=time(16))
    restarted.eta_history.async_trips = AsyncMock(return_value=[])
    await update(restarted, replace(approach()[0], timestamp=BASE.replace(hour=14)))
    assert student.eta_status == "unknown"
    # A fresh next morning cannot inherit yesterday's completed pickup.
    await update(restarted, replace(approach()[0], timestamp=BASE + timedelta(days=1)))
    assert student.stop_visit_inferred is False
    assert student.eta_status == "unknown"


@pytest.mark.parametrize(
    ("enabled", "history", "direction", "speed"),
    [
        (False, True, True, 0),
        (True, False, True, 0),
        (True, True, False, 0),
        (True, True, True, 10),
    ],
)
async def test_stop_inference_rejects_unsupported_visits(
    hass: HomeAssistant, *, enabled: bool, history: bool, direction: bool, speed: int
) -> None:
    """Require the toggle, historical stops, matching direction, and low speed."""
    hass.config.components.add("recorder")
    coordinator = HCBDataCoordinator(
        hass,
        MagicMock(
            data={"update_interval": 20},
            entry_id="entry",
            options={CONF_INFER_STOP: enabled},
        ),
    )
    coordinator.eta_history.async_trips = AsyncMock(
        return_value=trips() if history else []
    )
    student = StudentData(
        "Alice",
        "s",
        eta_stops={"am": STOP},
        display_on_map=True,
        latent=False,
        speed=speed,
    )
    for point in approach():
        student.latitude = point.latitude if direction else 70 - point.latitude
        student.longitude, student.log_time = point.longitude, point.timestamp
        with patch(
            "custom_components.here_comes_the_bus.coordinator.dt_util.now",
            return_value=point.timestamp,
        ):
            await coordinator._async_update_eta(student)
    assert student.eta_status != "done"
    assert student.stop_visit_inferred is not True


def test_binary_inference_attributes(hass: HomeAssistant) -> None:
    """Make the assumed boarding/alighting status available to automations."""
    student = StudentData("Alice", "s", stop_visit_inferred=True, eta_period="am")
    coordinator = HCBDataCoordinator(
        hass, MagicMock(data={"update_interval": 20}, entry_id="entry")
    )
    description = next(
        item for item in BINARY_DESCRIPTIONS if item.key == "stop_visit_inferred"
    )
    binary = HCBBinarySensor(coordinator, description, student)
    assert binary.is_on is True
    assert binary.extra_state_attributes == {"period": "am", "assumed_on_bus": True}
    student.eta_period = "pm"
    assert binary.extra_state_attributes["assumed_on_bus"] is False
    student.eta_period = "mid"
    assert binary.extra_state_attributes["assumed_on_bus"] is None
    assert (
        HCBBinarySensor(
            coordinator, BINARY_DESCRIPTIONS[0], student
        ).extra_state_attributes
        is None
    )


async def test_no_active_window(hass: HomeAssistant) -> None:
    """Do not calculate an ETA outside service hours even with a known destination."""
    hass.config.components.add("recorder")
    coordinator = HCBDataCoordinator(
        hass, MagicMock(data={"update_interval": 20}, entry_id="entry")
    )
    student = StudentData("Alice", "s", eta_stops={"am": STOP})
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=BASE.replace(hour=5),
    ):
        await coordinator._async_update_eta(student)
    assert student.eta_status == "unknown"


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.usefixtures("recorder_db_url")
@pytest.mark.freeze_time("2026-08-31T06:00:00+00:00")
async def test_real_recorder_round_trip(
    hass: HomeAssistant, recorder_mock: Any, freezer: Any, *, legacy: bool
) -> None:
    """Recover trips through recorder, including attribute-only updates."""
    dt_util.set_default_time_zone(UTC)
    config_entry = MockConfigEntry(domain=DOMAIN, entry_id="entry")
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    tracker = registry.async_get_or_create(
        "device_tracker", DOMAIN, "alice_bus_location", config_entry=config_entry
    )
    log = registry.async_get_or_create(
        "sensor", DOMAIN, "alice_bus_log_time", config_entry=config_entry
    )
    for offset in (2, 1):
        for point in approach(BASE - timedelta(days=offset)):
            freezer.move_to(point.timestamp)
            attrs = {"latitude": point.latitude, "longitude": point.longitude}
            if not legacy:
                attrs.update(
                    {
                        "eta_log_time": point.timestamp.isoformat(),
                        "eta_gps_valid": True,
                        "eta_speed": 0,
                    }
                )
            hass.states.async_set(tracker.entity_id, "unchanged address", attrs)
            hass.states.async_set(log.entity_id, point.timestamp.isoformat())
            await hass.async_block_till_done()
    await recorder_mock.async_block_till_done()
    freezer.move_to(BASE)
    history = History(hass, "entry")
    learned = await history.async_trips(StudentData("Alice", "s"), "am", STOP, BASE)
    assert len(learned) == 2
    result = estimate(learned, approach()[2], approach()[1])
    assert result.minutes(approach()[2].timestamp) == 2


def test_legacy_alignment_without_location() -> None:
    """Never invent positions for a log timestamp preceding tracker history."""
    logs = [State("sensor.log", BASE.isoformat(), last_updated=BASE)]
    assert list(align_legacy_fixes([], logs)) == []


def test_interpolation_and_parallel_street() -> None:
    """Interpolate between recorded fixes but reject a nearby parallel road."""
    before = approach()[1]
    current = replace(
        approach()[2], latitude=35.005, timestamp=BASE + timedelta(seconds=90)
    )
    assert estimate(trips(), current, before).minutes(current.timestamp) == 2.5
    # A parallel street about 180 meters away has the same heading but is off-route.
    assert (
        estimate(
            trips(),
            replace(current, longitude=-80.002),
            replace(before, longitude=-80.002),
        ).arrival
        is None
    )


async def test_missing_recorder_pauses_only_estimates_and_recovers(
    hass: HomeAssistant,
) -> None:
    """Keep reported data and explain missing Recorder, including delayed startup."""
    coordinator = HCBDataCoordinator(
        hass, MagicMock(data={}, entry_id="no-recorder", options={})
    )
    coordinator.eta_history.async_trips = AsyncMock(return_value=trips())
    student = StudentData(
        "Alice",
        "s",
        eta_stops={"am": STOP},
        display_on_map=True,
        latent=False,
        bus_name="123",
        speed=15,
        stop_eta=5,
        eta_announcements_allowed=True,
        stop_visit_inferred=True,
    )
    coordinator.data = {student.student_id: student}
    details = next(item for item in ENTITY_DESCRIPTIONS if item.key == "eta_details")
    with patch.object(coordinator, "_student_is_moving", return_value=False):
        await coordinator._async_update_data()
    assert student.bus_name == "123"
    assert student.speed == 15
    assert student.stop_eta is None
    assert student.stop_visit_inferred is None
    assert not student.eta_announcements_allowed
    assert details.value_fn(student) == (
        "Arrival estimates are paused because Home Assistant Recorder is not enabled."
    )
    coordinator.eta_history.async_trips.assert_not_awaited()
    assert coordinator._eta_journeys == {}

    hass.config.components.add("recorder")
    for point in approach()[1:3]:
        student.latitude = point.latitude
        student.longitude = point.longitude
        student.log_time = point.timestamp
        with patch(
            "custom_components.here_comes_the_bus.coordinator.dt_util.now",
            return_value=point.timestamp,
        ):
            await coordinator._async_update_eta(student)
    assert student.stop_eta == 2
    assert student.eta_status == "tracking"
    assert student.eta_announcements_allowed

    hass.config.components.remove("recorder")
    await coordinator._async_update_eta(student)
    assert student.stop_eta is None
    assert not student.eta_announcements_allowed
    assert student.eta_estimate.reason == "recorder_disabled"
