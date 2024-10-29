"""Tests for the Here Comes The Bus binary sensor."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.here_comes_the_bus.binary_sensor import (
    ENTITY_DESCRIPTIONS,
    HCBBinarySensor,
    _message_code_to_bool,
    async_setup_entry,
)
from custom_components.here_comes_the_bus.const import BUS
from custom_components.here_comes_the_bus.data import StudentData


@pytest.fixture(autouse=True)
def skip_first_refresh() -> Generator:
    """Skip the first refresh."""
    with patch(
        "custom_components.here_comes_the_bus.coordinator.HCBDataCoordinator.async_config_entry_first_refresh",
        return_value=None,
    ):
        yield


def test_message_code_to_bool() -> None:
    """Test the _message_code_to_bool function."""
    assert _message_code_to_bool(1) is True
    assert _message_code_to_bool(0) is False
    assert _message_code_to_bool(None) is None


async def test_binary_sensor_setup_entry(hass: HomeAssistant) -> None:
    """Test the async_setup_entry function."""
    entry = MagicMock()
    coordinator = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator.data = {
        "student1": StudentData(first_name="Alice", student_id="student1"),
        "student2": StudentData(first_name="Bob", student_id="student2"),
    }
    entry.runtime_data = MagicMock(coordinator=coordinator)
    async_add_entities = AsyncMock()

    await async_setup_entry(hass, entry, async_add_entities)

    # Convert the generator expression to a list
    sensors = list(async_add_entities.call_args[0][0])

    # Assert that async_add_entities was called with a list of the expected sensors
    assert async_add_entities.call_count == 1
    assert len(sensors) == len(ENTITY_DESCRIPTIONS) * len(coordinator.data)


async def test_binary_sensor_properties() -> None:
    """Test the properties of the HCBBinarySensor class."""
    coordinator = AsyncMock()
    student = StudentData(first_name="Alice", student_id="student1", ignition=True)
    description = ENTITY_DESCRIPTIONS[0]
    sensor = HCBBinarySensor(coordinator, description, student)

    assert sensor.name == f"{student.first_name} {BUS} {description.name}"
    assert sensor.unique_id == f"{student.first_name}_{BUS}_{description.key}".lower()
    assert sensor.device_class == description.device_class
    assert sensor.is_on is True
    assert sensor.icon == description.icon_on

    student.ignition = False
    coordinator.data = {student.student_id: student}

    with patch.object(sensor, "async_write_ha_state") as mock_write_state:
        sensor._handle_coordinator_update()
        mock_write_state.assert_called_once()  # Verify async_write_ha_state is called

    assert sensor.is_on is False
    assert sensor.icon == description.icon


async def test_binary_sensor_no_value_fn() -> None:
    """Test the HCBBinarySensor class when no value_fn is provided."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1")
    description = ENTITY_DESCRIPTIONS[2]  # "In Service" sensor has no value_fn
    sensor = HCBBinarySensor(coordinator, description, student)

    assert sensor.is_on is None
    assert sensor.icon == "mdi:flag-off"


async def test_binary_sensor_coordinator_update_empty_data() -> None:
    """Test the _handle_coordinator_update method when coordinator data is empty."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1")
    description = ENTITY_DESCRIPTIONS[0]
    sensor = HCBBinarySensor(coordinator, description, student)

    coordinator.data = {}
    with patch.object(sensor, "async_write_ha_state") as mock_write_state:
        sensor._handle_coordinator_update()
        mock_write_state.assert_not_called()


async def test_binary_sensor_coordinator_update_no_student() -> None:
    """Test the _handle_coordinator_update method when student not in the data."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1")
    description = ENTITY_DESCRIPTIONS[0]
    sensor = HCBBinarySensor(coordinator, description, student)

    coordinator.data = {
        "student2": StudentData(first_name="Bob", student_id="student2")
    }
    with patch.object(sensor, "async_write_ha_state") as mock_write_state:
        sensor._handle_coordinator_update()
        mock_write_state.assert_not_called()


async def test_handle_coordinator_update() -> None:
    """Test the _handle_coordinator_update method."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1")
    student.ignition = True
    description = ENTITY_DESCRIPTIONS[0]
    sensor = HCBBinarySensor(coordinator, description, student)

    # Test with non-empty data
    coordinator.data = {student.student_id: student}
    with patch.object(sensor, "async_write_ha_state") as mock_write_state:
        sensor._handle_coordinator_update()
        mock_write_state.assert_called_once()
