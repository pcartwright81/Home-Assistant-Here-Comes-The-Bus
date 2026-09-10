"""Test the sensor module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.here_comes_the_bus.data import StudentData
from custom_components.here_comes_the_bus.eta import Estimate
from custom_components.here_comes_the_bus.sensor import (
    ENTITY_DESCRIPTIONS,
    HCBSensor,
    async_setup_entry,
)


@pytest.mark.parametrize("eta_enabled", [True, False])
async def test_sensor_setup_entry(hass: HomeAssistant, *, eta_enabled: bool) -> None:
    """Test the async_setup_entry function."""
    entry = MagicMock()
    coordinator = MagicMock()
    coordinator.eta_enabled = eta_enabled
    coordinator.data = {
        "student1": StudentData(
            first_name="Alice", student_id="student1", has_mid_stops=True
        ),
        "student2": StudentData(
            first_name="Bob", student_id="student2", has_mid_stops=False
        ),
    }
    entry.runtime_data = MagicMock(coordinator=coordinator)
    async_add_entities = AsyncMock()

    await async_setup_entry(hass, entry, async_add_entities)

    # Convert the generator expression to a list
    sensors = list(async_add_entities.call_args[0][0])

    # Assert that async_add_entities was called with the expected sensors
    assert async_add_entities.call_count == 1
    # Total sensors should be all sensors for student1 + non-mid sensors for student2
    expected_sensor_count = len(ENTITY_DESCRIPTIONS) + (
        len(ENTITY_DESCRIPTIONS) - 2
    )  # 2 mid sensors
    if not eta_enabled:
        expected_sensor_count -= 3 * len(coordinator.data)
    assert len(sensors) == expected_sensor_count
    if not eta_enabled:
        assert not {sensor.entity_description.key for sensor in sensors}.intersection(
            ("stop_eta", "eta_status", "eta_details")
        )


async def test_sensor_properties() -> None:
    """Test the properties of the HCBSensor class."""
    coordinator = MagicMock()
    student = StudentData(
        first_name="Alice",
        student_id="student1",
        bus_name="Bus 123",
        speed=25,
    )
    description = ENTITY_DESCRIPTIONS[0]  # "bus_name" sensor
    sensor = HCBSensor(coordinator, description, student)

    assert sensor.native_value == student.bus_name
    assert sensor.device_class == description.device_class

    # Test with a different sensor (speed)
    description = ENTITY_DESCRIPTIONS[1]  # "speed" sensor
    sensor = HCBSensor(coordinator, description, student)
    assert sensor.native_value == student.speed
    assert sensor.native_unit_of_measurement == "mph"


async def test_sensor_coordinator_update_empty_data() -> None:
    """Test _handle_coordinator_update with empty data."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1")
    description = ENTITY_DESCRIPTIONS[0]
    sensor = HCBSensor(coordinator, description, student)

    coordinator.data = {}
    with patch.object(sensor, "async_write_ha_state") as mock_write_state:
        sensor._handle_coordinator_update()
        mock_write_state.assert_not_called()


async def test_sensor_coordinator_update_no_student() -> None:
    """Test _handle_coordinator_update when student not in data."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1")
    description = ENTITY_DESCRIPTIONS[0]
    sensor = HCBSensor(coordinator, description, student)

    coordinator.data = {
        "student2": StudentData(first_name="Bob", student_id="student2")
    }
    with patch.object(sensor, "async_write_ha_state") as mock_write_state:
        sensor._handle_coordinator_update()
        mock_write_state.assert_not_called()


async def test_sensor_coordinator_update() -> None:
    """Test _handle_coordinator_update with valid data."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1", speed=25)
    description = ENTITY_DESCRIPTIONS[1]  # "speed" sensor
    sensor = HCBSensor(coordinator, description, student)

    coordinator.data = {student.student_id: student}
    with patch.object(sensor, "async_write_ha_state") as mock_write_state:
        sensor._handle_coordinator_update()
        mock_write_state.assert_called_once()


async def test_native_value_with_valid_value_fn() -> None:
    """Test native_value with a valid value_fn."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1", bus_name="Bus 123")
    description = ENTITY_DESCRIPTIONS[0]  # "bus_name" sensor
    sensor = HCBSensor(coordinator, description, student)

    assert sensor.native_value == student.bus_name


@pytest.mark.parametrize(
    ("estimate", "expected"),
    [
        (None, "Waiting for a fresh bus location."),
        (Estimate(), "Waiting for a fresh bus location."),
        (
            Estimate(reason="insufficient_history", available_trips=1),
            "Learning route: needs at least 2 completed trips (1 available).",
        ),
        (
            Estimate(reason="matched", matching_trips=3, confidence="consistent"),
            "Tracking arrival using 3 matching trips.",
        ),
        (
            Estimate(reason="matched", matching_trips=2, confidence="divergent"),
            "Past trips give conflicting arrival estimates; announcements paused.",
        ),
        (
            Estimate(reason="completed", source="reported_arrival"),
            "Arrival reported by Here Comes The Bus.",
        ),
        (
            Estimate(reason="completed", source="inferred_stop"),
            "Stop visit inferred from bus location; arrival is not confirmed.",
        ),
        (Estimate(reason="gps_stale"), "Waiting for a fresh bus location."),
        (
            Estimate(reason="no_destination"),
            "No stop is available for the current service period.",
        ),
        (
            Estimate(reason="outside_service_window"),
            "Waiting for the next service period.",
        ),
        (Estimate(reason="gps_hidden"), "Bus location is not being shared."),
        (Estimate(reason="gps_invalid"), "Waiting for a valid bus location."),
        (
            Estimate(reason="gps_out_of_order"),
            "Received an older bus location; waiting for an update.",
        ),
        (
            Estimate(reason="insufficient_movement"),
            "Waiting for more bus movement to match the route.",
        ),
        (
            Estimate(reason="ambiguous_route"),
            "Bus location matches multiple parts of past routes.",
        ),
        (
            Estimate(
                reason="insufficient_matches", available_trips=5, matching_trips=1
            ),
            "Matching past trips: 1 of 5; at least 2 needed for an estimate.",
        ),
        (
            Estimate(reason="prediction_expired"),
            "Previous estimate has expired; waiting for a new estimate.",
        ),
        (
            Estimate(reason="passed"),
            "Bus passed the stop's final approach; arrival is not confirmed.",
        ),
        (Estimate(reason="future_reason"), "Waiting for an arrival estimate."),
    ],
)
async def test_estimated_arrival_details(
    estimate: Estimate | None, expected: str
) -> None:
    """Explain missing estimates, route confidence, and distinct arrival sources."""
    student = StudentData(
        first_name="Alice", student_id="student1", eta_estimate=estimate
    )
    description = next(
        item for item in ENTITY_DESCRIPTIONS if item.key == "eta_details"
    )
    sensor = HCBSensor(MagicMock(), description, student)

    assert sensor.native_value == expected
    assert sensor.extra_state_attributes is None
