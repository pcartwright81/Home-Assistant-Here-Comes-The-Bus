"""Tests the entitiy module."""

from unittest.mock import MagicMock

from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.here_comes_the_bus.const import BUS, DOMAIN, HERE_COMES_THE_BUS
from custom_components.here_comes_the_bus.data import StudentData
from custom_components.here_comes_the_bus.entity import HCBEntity


async def test_hcb_entity_properties() -> None:
    """Test the properties of the HCBEntity class."""
    coordinator = MagicMock()
    student = StudentData(first_name="Alice", student_id="student1")
    description = MagicMock(name="Test Sensor", key="test_sensor")
    entity = HCBEntity(coordinator, student, description)

    assert entity.name == f"{student.first_name} {BUS} {description.name}"
    assert entity.unique_id == f"{student.first_name}_{BUS}_{description.key}".lower()
    assert entity.icon == "mdi:bus"
    assert entity.device_info == {
        "entry_type": DeviceEntryType.SERVICE,
        "identifiers": {(DOMAIN, student.student_id)},
        "manufacturer": HERE_COMES_THE_BUS,
        "name": f"{student.first_name} {BUS}",
    }
