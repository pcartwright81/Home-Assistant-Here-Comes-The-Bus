"""Test the device tracker module."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.here_comes_the_bus.data import (
    StudentData,  # pylint: disable=import-outside-toplevel
)
from custom_components.here_comes_the_bus.device_tracker import (  # pylint: disable=import-outside-toplevel
    DEVICE_TRACKERS,
    HCBTracker,
    async_setup_entry,
)


async def test_device_tracker_setup_entry(hass: HomeAssistant) -> None:
    """Test the async_setup_entry function."""
    entry = MagicMock()
    coordinator = MagicMock()
    coordinator.data = {
        "student1": StudentData(first_name="Alice", student_id="student1"),
        "student2": StudentData(first_name="Bob", student_id="student2"),
    }
    entry.runtime_data = MagicMock(coordinator=coordinator)
    async_add_entities = AsyncMock()

    await async_setup_entry(hass, entry, async_add_entities)

    # Convert the generator expression to a list before checking its length
    entities = list(async_add_entities.call_args[0][0])

    # Assert that async_add_entities was called with the expected device trackers
    assert async_add_entities.call_count == 1
    assert len(entities) == len(DEVICE_TRACKERS) * len(coordinator.data)


async def test_device_tracker_properties() -> None:
    """Test the properties of the HCBTracker class."""
    coordinator = MagicMock()
    student = StudentData(
        first_name="Alice",
        student_id="student1",
        latitude=37.7749,
        longitude=-122.4194,
        address="123 Main St",
    )

    description = DEVICE_TRACKERS[0]
    tracker = HCBTracker(coordinator, student, description)

    assert tracker.location_name == student.address
    assert tracker.latitude == student.latitude
    assert tracker.longitude == student.longitude
    assert tracker.location_accuracy == 100  # noqa: PLR2004

    # Test with empty coordinator data
    coordinator.data = {}
    with patch.object(tracker, "async_write_ha_state") as mock_write_state:
        tracker._handle_coordinator_update()
        mock_write_state.assert_not_called()

    # Test with coordinator data containing the student
    coordinator.data = {student.student_id: student}
    with patch.object(tracker, "async_write_ha_state") as mock_write_state:
        tracker._handle_coordinator_update()
        mock_write_state.assert_called_once()

    # Test with coordinator data not containing the student
    coordinator.data = {
        "student2": StudentData(first_name="Bob", student_id="student2")
    }
    with patch.object(tracker, "async_write_ha_state") as mock_write_state:
        tracker._handle_coordinator_update()
        mock_write_state.assert_not_called()
