"""Test the sensor module."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.here_comes_the_bus.data import StudentData
from custom_components.here_comes_the_bus.sensor import (
    ENTITY_DESCRIPTIONS,
    HCBSensor,
    async_setup_entry,
)


async def test_sensor_setup_entry(hass: HomeAssistant) -> None:
    """Test the async_setup_entry function."""
    entry = MagicMock()
    coordinator = MagicMock()
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
    assert len(sensors) == expected_sensor_count


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
