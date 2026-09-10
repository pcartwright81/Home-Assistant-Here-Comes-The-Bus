"""Test arrival labels, archive boundaries, and estimate uncertainty."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.here_comes_the_bus.const import DOMAIN
from custom_components.here_comes_the_bus.coordinator import HCBDataCoordinator
from custom_components.here_comes_the_bus.data import StudentData
from custom_components.here_comes_the_bus.eta import (
    Estimate,
    completed_trip,
    estimate,
    reported_trip,
)
from custom_components.here_comes_the_bus.eta_archive import (
    ARCHIVE_TRIPS,
    Archive,
    archive_key,
    decode_trip,
    encode_trip,
)
from custom_components.here_comes_the_bus.eta_history import History, reported_arrival
from custom_components.here_comes_the_bus.sensor import ENTITY_DESCRIPTIONS, HCBSensor

from .test_eta import BASE, STOP, approach, trips


def test_reported_arrival_recovers_missed_stationary_fix() -> None:
    """A reported endpoint may label a slow approach without claiming a GPS stop."""
    points = [replace(p, speed=4) for p in approach()]
    arrival = points[4].timestamp
    assert completed_trip(points, STOP) is None
    trip = reported_trip([*points, points[-1]], STOP, arrival)
    assert trip.source == "reported_arrival"
    assert trip.arrival == arrival
    assert trip.direction == 180
    assert len(trip.points) == 5


@pytest.mark.parametrize(
    "mode", ["empty", "gap", "far", "away", "stationary", "direction", "other_day"]
)
def test_reported_arrival_needs_corroboration(mode: str) -> None:
    """An arrival string alone cannot label unrelated, stale, or reversing GPS."""
    points = approach()[:3]
    arrival = approach()[4].timestamp
    direction = None
    if mode == "empty":
        points = []
    elif mode == "gap":
        arrival += timedelta(minutes=5)
    elif mode == "far":
        points = [replace(p, longitude=-81) for p in points]
    elif mode == "away":
        points = [replace(p, latitude=35.004 + i * 0.002) for i, p in enumerate(points)]
    elif mode == "stationary":
        points = [replace(p, latitude=35.002) for p in points]
    elif mode == "direction":
        direction = 0
    else:
        arrival += timedelta(days=1)
    assert reported_trip(points, STOP, arrival, direction) is None


def test_reported_labels_exclude_old_and_conflicting_times() -> None:
    """Only a new same-day value, recorded near arrival, is a usable endpoint."""
    arrival = BASE + timedelta(minutes=4)
    valid = State(
        "sensor.arrival", "07:04:00", last_changed=arrival + timedelta(seconds=5)
    )
    stale = State("sensor.arrival", "07:04:00", last_changed=BASE - timedelta(days=1))
    invalid = State("sensor.arrival", "unknown", last_changed=BASE)
    assert reported_arrival([invalid, stale], BASE) is None
    assert reported_arrival([invalid, stale, valid], BASE) == arrival
    other = State(
        "sensor.arrival", "07:05:00", last_changed=BASE + timedelta(minutes=5)
    )
    assert reported_arrival([valid, other], BASE) is None
    disconnected = [
        *approach()[:2],
        replace(approach()[2], timestamp=BASE + timedelta(minutes=5)),
    ]
    assert reported_trip(disconnected, STOP, BASE + timedelta(minutes=5)) is None


async def test_reported_completion_persists_without_inferred_boarding(
    hass: HomeAssistant,
) -> None:
    """A new service arrival completes the trip even after map tracking is hidden."""
    hass.config.components.add("recorder")
    entry = MagicMock(data={"update_interval": 20}, entry_id="reported", options={})
    coordinator = HCBDataCoordinator(hass, entry)
    coordinator.eta_history.async_trips = AsyncMock(return_value=trips())
    coordinator.eta_history.async_remember = AsyncMock()
    student = StudentData(
        "Alice", "s", eta_stops={"am": STOP}, display_on_map=True, latent=False
    )
    for point in approach()[:3]:
        student.latitude, student.longitude, student.log_time = (
            point.latitude,
            point.longitude,
            point.timestamp,
        )
        with patch(
            "custom_components.here_comes_the_bus.coordinator.dt_util.now",
            return_value=point.timestamp,
        ):
            await coordinator._async_update_eta(student)
    arrival = approach()[4].timestamp
    student.am_stop_arrival_time = arrival.time()
    student.display_on_map = False
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=arrival,
    ):
        await coordinator._async_update_eta(student)
        assert student.eta_status == "done"
        assert student.stop_eta == 0
        assert student.stop_visit_inferred is None
        assert student.eta_estimate.source == "reported_arrival"
        assert not student.eta_announcements_allowed
        coordinator.eta_history.async_remember.assert_awaited_once()
        restarted = HCBDataCoordinator(hass, entry)
        await restarted._async_load_eta_completion()
        await restarted._async_update_eta(student)
        assert student.eta_status == "done"
        assert student.eta_estimate.source == "reported_arrival"
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=arrival + timedelta(days=1),
    ):
        await restarted._async_update_eta(student)
    assert student.eta_status == "unknown"


@pytest.mark.parametrize("mode", ["unchanged", "future", "far", "no_journey"])
async def test_live_report_rejects_uncorroborated_values(
    hass: HomeAssistant, mode: str
) -> None:
    """Do not infer completion from a carried-over time or an unrelated journey."""
    hass.config.components.add("recorder")
    coordinator = HCBDataCoordinator(
        hass, MagicMock(data={}, entry_id="reject", options={})
    )
    coordinator.eta_history.async_trips = AsyncMock(return_value=[])
    student = StudentData(
        "Alice", "s", eta_stops={"am": STOP}, display_on_map=True, latent=False
    )
    arrival = approach()[4].timestamp
    if mode == "unchanged":
        student.am_stop_arrival_time = arrival.time()
    for point in approach()[:3]:
        student.latitude, student.longitude, student.log_time = (
            point.latitude,
            (-81 if mode == "far" else point.longitude),
            point.timestamp,
        )
        if mode == "no_journey":
            student.display_on_map = False
        with patch(
            "custom_components.here_comes_the_bus.coordinator.dt_util.now",
            return_value=point.timestamp,
        ):
            await coordinator._async_update_eta(student)
    student.am_stop_arrival_time = (
        (arrival + timedelta(minutes=5)).time() if mode == "future" else arrival.time()
    )
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=arrival,
    ):
        await coordinator._async_update_eta(student)
    assert student.eta_status != "done"


async def test_archive_survives_reload_and_bounds_training(hass: HomeAssistant) -> None:
    """Persist capped examples, replace inference with reports, and exclude today."""
    archive = Archive(hass, "archive")
    key = archive_key("s", "am", STOP, None)
    examples = [
        completed_trip(approach(BASE - timedelta(days=i)), STOP) for i in range(-1, 66)
    ]
    await archive.async_merge(key, examples, BASE + timedelta(hours=2))
    assert len(archive.records[key]) == ARCHIVE_TRIPS
    assert len(archive.trips(key, BASE)) == ARCHIVE_TRIPS - 1
    reported = replace(examples[2], source="reported_arrival")
    await archive.async_merge(key, [reported], BASE)
    await archive.async_merge(key, [examples[2]], BASE)
    await archive.async_merge(
        key, [replace(reported, points=reported.points[1:])], BASE
    )
    restored = Archive(hass, "archive")
    await restored.async_load()
    assert (
        next(t for t in restored.records[key] if t.arrival == reported.arrival).source
        == "reported_arrival"
    )
    assert restored.records == archive.records
    assert (
        next(t for t in restored.records[key] if t.arrival == reported.arrival).points
        == reported.points
    )
    assert restored.trips(key, BASE + timedelta(days=100)) == []
    changed = archive_key("s", "am", replace(STOP, stop_id="new"), None)
    await restored.async_merge(changed, [reported], BASE)
    assert key not in restored.records
    assert len(restored.records[changed]) == 1
    await restored.async_merge(changed, [], BASE + timedelta(days=100))
    assert restored.records == {}


async def test_archive_skips_corrupt_records(hass: HomeAssistant) -> None:
    """Ignore malformed identities and invalid GPS, preserving valid routes."""
    archive = Archive(hass, "corrupt")
    key = archive_key("s", "am", STOP, None)
    valid = encode_trip(trips()[0])
    bad = {**valid, "points": [["bad", 0, 0, 0]]}
    archive.store.async_load = AsyncMock(
        return_value={"bad json": [], "[]": [], key: [bad]}
    )
    await archive.async_load()
    assert archive.records == {}
    with pytest.raises(ValueError, match="Invalid archived trip"):
        decode_trip(bad)
    assert decode_trip(valid) == trips()[0]
    archive.loaded = False
    archive.store.async_load = AsyncMock(return_value=["broken"])
    await archive.async_load()
    assert archive.records == {}


async def test_history_uses_archive_when_recorder_is_missing(
    hass: HomeAssistant,
) -> None:
    """Recorder failures and disabled recorder do not erase learned routes."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="offline")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "device_tracker", DOMAIN, "alice_bus_location", config_entry=entry
    )
    history = History(hass, "offline")
    student = StudentData("Alice", "s")
    key = archive_key("s", "am", STOP, None)
    await history.archive.async_merge(key, trips(), BASE)
    assert len(await history.async_trips(student, "am", STOP, BASE)) == 2
    hass.config.components.add("recorder")
    arrival = registry.async_get_or_create(
        "sensor", DOMAIN, "alice_bus_am_stop_arrival_time", config_entry=entry
    )
    worker = AsyncMock(return_value=trips())
    with patch(
        "homeassistant.components.recorder.get_instance",
        return_value=MagicMock(async_add_executor_job=worker),
    ):
        assert len(await history.async_trips(student, "am", STOP, BASE)) == 2
    assert worker.call_args.args[-1] == arrival.entity_id
    history.cache.clear()
    with patch(
        "homeassistant.components.recorder.get_instance",
        return_value=MagicMock(async_add_executor_job=AsyncMock(side_effect=OSError)),
    ):
        assert len(await history.async_trips(student, "am", STOP, BASE)) == 2
        assert len(await history.async_trips(student, "am", STOP, BASE)) == 2
    history.archive.store.async_save = AsyncMock(side_effect=OSError)
    await history.async_remember(
        student, "am", STOP, BASE, completed_trip(approach(), STOP)
    )
    history.archive.async_load = AsyncMock(side_effect=OSError)
    assert len(await history.async_trips(student, "am", STOP, BASE)) == 2


def test_recorder_training_uses_reported_arrivals(hass: HomeAssistant) -> None:
    """Recover historical routes whose sampled pickup speed never reached zero."""
    dt_util.set_default_time_zone(UTC)
    history = History(hass, "labels")

    def read(
        _hass: HomeAssistant,
        start: datetime,
        _end: datetime,
        entities: list[str],
        **_kwargs: object,
    ) -> dict:
        arrival = start.replace(hour=7, minute=4)
        return {
            entities[0]: [
                State(
                    entities[0], "07:04:00", last_changed=arrival + timedelta(seconds=5)
                )
            ]
        }

    def points(_entity: str, start: datetime, *_args: object) -> list:
        return [replace(p, speed=4) for p in approach(start.replace(hour=7))]

    with (
        patch(
            "homeassistant.components.recorder.history.get_significant_states",
            side_effect=read,
        ),
        patch.object(history, "_day_points", side_effect=points),
    ):
        learned = history._load(
            "device_tracker.bus", STOP, BASE, arrival_id="sensor.arrival"
        )
    assert len(learned) == 10
    assert all(t.source == "reported_arrival" for t in learned)


def test_uncertainty_and_diagnostics(hass: HomeAssistant) -> None:
    """Expose disagreement without labeling a descriptive range as a probability."""
    before, point = approach()[1:3]
    history = trips()
    result = estimate(history, point, before)
    assert result.confidence == "limited"
    assert result.available_trips == result.matching_trips == 2
    divergent = estimate(
        [
            history[0],
            replace(history[1], arrival=history[1].arrival + timedelta(minutes=6)),
        ],
        point,
        before,
    )
    assert divergent.confidence == "divergent"
    assert divergent.latest_arrival - divergent.earliest_arrival == timedelta(minutes=6)
    student = StudentData("Alice", "s")
    coordinator = HCBDataCoordinator(hass, MagicMock(data={}, entry_id="confidence"))
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=point.timestamp,
    ):
        coordinator._set_eta_estimate(student, divergent)
    assert student.eta_status == "tracking"
    assert not student.eta_announcements_allowed
    sensor = HCBSensor(
        coordinator,
        next(d for d in ENTITY_DESCRIPTIONS if d.key == "stop_eta"),
        student,
    )
    assert sensor.extra_state_attributes["confidence"] == "divergent"
    assert sensor.extra_state_attributes["earliest_arrival"] is not None
    assert estimate([], point, before).reason == "insufficient_history"
    assert (
        estimate(history, replace(point, longitude=-81), before).reason
        == "insufficient_matches"
    )
    with patch(
        "custom_components.here_comes_the_bus.coordinator.dt_util.now",
        return_value=BASE,
    ):
        coordinator._set_eta_estimate(student, Estimate(BASE - timedelta(seconds=1)))
    assert student.eta_estimate.reason == "prediction_expired"
    student.latitude, student.longitude = 0, 0
    student.display_on_map = True
    student.latent = False
    assert (
        coordinator._eta_position_reason(student, STOP, BASE, moving=True)
        == "gps_invalid"
    )


async def test_archive_retries_failed_save_without_losing_previous_partition(
    hass: HomeAssistant,
) -> None:
    """A failed write must not make an unsaved replacement look persisted."""
    archive = Archive(hass, "retry")
    old_key = archive_key("s", "am", STOP, None)
    await archive.async_merge(old_key, trips(), BASE)
    previous = dict(archive.records)
    new_key = archive_key("s", "am", replace(STOP, stop_id="new"), None)
    archive.store.async_save = AsyncMock(side_effect=[OSError("disk full"), None])

    with pytest.raises(OSError, match="disk full"):
        await archive.async_merge(new_key, trips(), BASE)
    assert archive.records == previous

    await archive.async_merge(new_key, trips(), BASE)
    assert archive.store.async_save.await_count == 2
    assert old_key not in archive.records
    assert archive.records[new_key] == previous[old_key]
    assert archive.store.async_save.call_args.args[0] == {
        new_key: [encode_trip(trip) for trip in archive.records[new_key]]
    }


async def test_history_refreshes_when_arrival_entity_changes(
    hass: HomeAssistant,
) -> None:
    """Registering or renaming the report sensor invalidates its cached model."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="arrival-rename")
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "device_tracker", DOMAIN, "alice_bus_location", config_entry=entry
    )
    hass.config.components.add("recorder")
    history = History(hass, entry.entry_id)
    student = StudentData("Alice", "s")
    worker = AsyncMock(return_value=trips())
    with patch(
        "homeassistant.components.recorder.get_instance",
        return_value=MagicMock(async_add_executor_job=worker),
    ):
        await history.async_trips(student, "am", STOP, BASE)
        assert worker.call_args.args[-1] is None
        arrival = registry.async_get_or_create(
            "sensor", DOMAIN, "alice_bus_am_stop_arrival_time", config_entry=entry
        )
        await history.async_trips(student, "am", STOP, BASE)
        assert worker.call_args.args[-1] == arrival.entity_id
        registry.async_update_entity(
            arrival.entity_id, new_entity_id="sensor.renamed_arrival"
        )
        await history.async_trips(student, "am", STOP, BASE)
        assert worker.call_args.args[-1] == "sensor.renamed_arrival"
        assert worker.await_count == 3
        assert len(history.cache) == 1


async def test_archive_enriches_existing_trips_with_street_labels(
    hass: HomeAssistant,
) -> None:
    """Reconstructed street information upgrades an otherwise identical old trip."""
    archive = Archive(hass, "street-upgrade")
    key = archive_key("s", "am", STOP, None)
    original = trips()[0]
    await archive.async_merge(key, [original], BASE)
    enriched = replace(
        original,
        points=tuple(replace(point, street="main street") for point in original.points),
    )
    await archive.async_merge(key, [enriched], BASE)
    await archive.async_merge(key, [original], BASE)
    restored = Archive(hass, "street-upgrade")
    await restored.async_load()
    assert restored.records[key] == [enriched]


async def test_completion_storage_failure_keeps_polling_and_retries(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A disk error must not break reported data or lose a pending completion save."""
    hass.config.components.add("recorder")
    coordinator = HCBDataCoordinator(
        hass, MagicMock(data={}, options={}, entry_id="completion-retry")
    )
    coordinator._eta_store.async_load = AsyncMock(side_effect=OSError("read failed"))
    await coordinator._async_load_eta_completion()
    assert "Unable to read bus ETA completion state" in caplog.text
    coordinator._reset_eta_cycle(BASE)
    coordinator._eta_arrived.add("completed-visit")
    coordinator._eta_store.async_save = AsyncMock(
        side_effect=[OSError("disk full"), None]
    )
    await coordinator._async_save_eta_completion(BASE)
    assert coordinator._eta_save_pending
    assert "will retry next update" in caplog.text
    student = StudentData("Alice", "s", bus_name="123", speed=15)
    coordinator.data = {student.student_id: student}
    with (
        patch(
            "custom_components.here_comes_the_bus.coordinator.dt_util.now",
            return_value=BASE,
        ),
        patch.object(coordinator, "_student_is_moving", return_value=False),
    ):
        result = await coordinator._async_update_data()
        assert not coordinator._eta_save_pending
        coordinator._eta_store.async_save.assert_awaited_with(
            {
                "day": BASE.date().isoformat(),
                "visits": ["completed-visit"],
                "reported": [],
                "suppressed": [],
            }
        )
        coordinator._eta_store.async_save.reset_mock()
        await coordinator._async_update_data()
        coordinator._eta_store.async_save.assert_not_awaited()
    assert result["s"].bus_name == "123"
    assert result["s"].speed == 15
