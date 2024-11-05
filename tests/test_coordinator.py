"""Tests for the Here Comes the Bus coordinator."""

from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.here_comes_the_bus.const import (
    CONF_SCHOOL_CODE,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from custom_components.here_comes_the_bus.coordinator import HCBDataCoordinator
from custom_components.here_comes_the_bus.data import StudentData

STUDENT_STOPS = [
    MagicMock(
        stop_type="School",
        time_of_day_id=HCBDataCoordinator.AM_ID,
        tier_start_time=time(6, 0),
        start_time=time(7, 15),
        am_school_arrival_time=time(7, 0),
        am_stopa_rrival_time=time(7, 15),
    ),
    MagicMock(
        stop_type="Stop",
        time_of_day_id=HCBDataCoordinator.AM_ID,
        tier_start_time=time(6, 0),
        start_time=time(7, 30),
        am_school_arrival_time=time(7, 0),
        am_stopa_rrival_time=time(7, 15),
    ),
]

LATITUDE = 37.7749
LONGITUDE = -122.4194
SPEED = 25


async def test_coordinator_init(hass: HomeAssistant) -> None:
    """Test coordinator initialization."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_UPDATE_INTERVAL: 30,
    }
    coordinator = HCBDataCoordinator(hass, config_entry)
    assert coordinator.name == DOMAIN
    assert coordinator.update_interval == timedelta(seconds=30)


async def test_async_config_entry_first_refresh(hass: HomeAssistant) -> None:
    """Test the async_config_entry_first_refresh method."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }
    config_entry.runtime_data = MagicMock(client=MagicMock())  # Add a mock client
    coordinator = HCBDataCoordinator(hass, config_entry)

    # Mock the client methods (access through config_entry)
    config_entry.runtime_data.client.get_school_id = AsyncMock(return_value="school_id")
    config_entry.runtime_data.client.get_parent_info = AsyncMock(
        return_value=MagicMock(
            account_id="parent_id",
            students=[
                MagicMock(first_name="Alice", student_id="student1"),
                MagicMock(first_name="Bob", student_id="student2"),
            ],
            times=[
                MagicMock(id=coordinator.AM_ID),
                MagicMock(id=coordinator.MID_ID),
                MagicMock(id=coordinator.PM_ID),
            ],
        )
    )
    config_entry.runtime_data.client.get_stop_info = AsyncMock(
        return_value=MagicMock(
            vehicle_location=MagicMock(),
            student_stops=STUDENT_STOPS,
        )
    )

    await coordinator.async_config_entry_first_refresh()

    assert coordinator._school_id == "school_id"
    assert coordinator._parent_id == "parent_id"
    expected_student_count = 2
    assert len(coordinator.data) == expected_student_count


async def test_async_update_data(hass: HomeAssistant) -> None:
    """Test the _async_update_data method."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }

    # Add a mock client to the config_entry
    config_entry.runtime_data = MagicMock(client=MagicMock())

    coordinator = HCBDataCoordinator(hass, config_entry)
    coordinator._school_id = "school_id"
    coordinator._parent_id = "parent_id"
    coordinator.data = {
        "student1": StudentData(
            first_name="Alice",
            student_id="student1",
        )
    }
    coordinator.data["student1"].am_start_time = time(7, 0)
    coordinator.data["student1"].am_end_time = time(8, 0)
    coordinator.data["student1"].has_mid_stops = True
    coordinator.data["student1"].mid_start_time = time(11, 0)
    coordinator.data["student1"].mid_end_time = time(12, 0)
    coordinator.data["student1"].pm_start_time = time(15, 0)
    coordinator.data["student1"].pm_end_time = time(16, 0)
    # Mock the client method (access through config_entry)
    config_entry.runtime_data.client.get_stop_info = AsyncMock(
        return_value=MagicMock(
            vehicle_location=MagicMock(),
            student_stops=STUDENT_STOPS,
        )
    )

    # Mock current time to be within AM range
    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=7, minute=30
        ),
    ):
        await coordinator._async_update_data()

    # Mock current time to be within MID range
    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=11, minute=30
        ),
    ):
        await coordinator._async_update_data()

    # Mock current time to be within PM range
    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=15, minute=30
        ),
    ):
        await coordinator._async_update_data()
    assert coordinator.data["student1"].log_time is not None


def test_update_vehicle_location_with_data() -> None:
    """Test _update_vehicle_location with valid vehicle_location data."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    student_data = StudentData(first_name="Alice", student_id="student1")
    dt_now = dt_util.now()
    vehicle_location = MagicMock(
        address="123 Main St",
        display_on_map=True,
        heading="N",
        ignition=True,
        latent=False,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        log_time=dt_now,
        message_code=1,
        speed=SPEED,
    )
    vehicle_location.configure_mock(name="Bus 123")
    coordinator._update_vehicle_location(student_data, vehicle_location)
    assert student_data.address == "123 Main St"
    assert student_data.bus_name == "Bus 123"
    assert student_data.display_on_map is True
    assert student_data.heading == "N"
    assert student_data.ignition is True
    assert student_data.latent is False
    assert student_data.latitude == LATITUDE
    assert student_data.longitude == LONGITUDE
    assert student_data.log_time == dt_now
    assert student_data.message_code == 1
    assert student_data.speed == SPEED


def test_update_vehicle_location_no_data() -> None:
    """Test _update_vehicle_location with empty vehicle_location data."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    student_data = StudentData(first_name="Alice", student_id="student1")

    coordinator._update_vehicle_location(student_data, None)
    assert student_data.address is None
    assert student_data.bus_name is None
    assert student_data.display_on_map is None
    assert student_data.heading is None
    assert student_data.ignition is None
    assert student_data.latent is None
    assert student_data.latitude is None
    assert student_data.longitude is None
    assert student_data.log_time is None
    assert student_data.message_code is None
    assert student_data.speed is None


def test_fix_time() -> None:
    """Test the _fix_time method."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )

    # Test with None input
    assert coordinator._fix_time(None) is None

    # Test with time(0) input
    assert coordinator._fix_time(time(0)) is None

    # Test with a valid time object
    input_time = time(10, 30, 15, 123456)
    expected_time = time(10, 30, 15)
    assert coordinator._fix_time(input_time) == expected_time


def test_get_time_of_day_id() -> None:
    """Test the _get_time_of_day_id method."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )

    # Test AM time
    assert coordinator._get_time_of_day_id(time(7, 0)) == coordinator.AM_ID

    # Test MID time
    assert coordinator._get_time_of_day_id(time(12, 0)) == coordinator.MID_ID

    # Test PM time
    assert coordinator._get_time_of_day_id(time(15, 0)) == coordinator.PM_ID


def test_update_stops_no_stops() -> None:
    """Test _update_stops with no stops."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    student_data = StudentData(first_name="Alice", student_id="student1")
    with pytest.raises(ValueError, match="No stops."):
        coordinator._update_stops(student_data, [])


def test_update_stops_mismatched_time_of_day() -> None:
    """Test _update_stops with mismatched time_of_day_id."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    student_data = StudentData(first_name="Alice", student_id="student1")
    stops = [
        MagicMock(time_of_day_id=coordinator.AM_ID),
        MagicMock(time_of_day_id=coordinator.MID_ID),
    ]
    with pytest.raises(
        ValueError, match="Time of day must match for this function to work"
    ):
        coordinator._update_stops(student_data, stops)  # type: ignore This is magic mock


def test_update_stops_am() -> None:
    """Test _update_stops with AM stops."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    student_data = StudentData(first_name="Alice", student_id="student1")
    stops = [
        MagicMock(
            time_of_day_id=coordinator.AM_ID,
            tier_start_time=time(7, 0),
            start_time=time(7, 15),
            stop_type="School",
            arrival_time=time(7, 30),
        ),
        MagicMock(
            time_of_day_id=coordinator.AM_ID,
            tier_start_time=time(7, 5),
            start_time=time(7, 20),
            stop_type="Stop",
            arrival_time=time(7, 45),
        ),
    ]
    coordinator._update_stops(student_data, stops)  # type: ignore This is magic mock
    assert student_data.am_start_time == time(7, 0)
    assert (
        student_data.am_end_time
        == (
            datetime.combine(dt_util.now().date(), time(7, 20)) + timedelta(minutes=30)
        ).time()
    )
    assert student_data.am_school_arrival_time == time(7, 30)
    assert student_data.am_stop_arrival_time == time(7, 45)


def test_update_stops_mid() -> None:
    """Test _update_stops with MID stops."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    student_data = StudentData(first_name="Alice", student_id="student1")
    stops = [
        MagicMock(
            time_of_day_id=coordinator.MID_ID,
            tier_start_time=time(12, 0),
            start_time=time(12, 15),
            stop_type="School",
            arrival_time=time(12, 30),
        ),
        MagicMock(
            time_of_day_id=coordinator.MID_ID,
            tier_start_time=time(12, 5),
            start_time=time(12, 20),
            stop_type="Stop",
            arrival_time=time(12, 45),
        ),
    ]
    coordinator._update_stops(student_data, stops)  # type: ignore This is magic mock
    assert student_data.mid_start_time == time(12, 0)
    assert (
        student_data.mid_end_time
        == (
            datetime.combine(dt_util.now().date(), time(12, 20)) + timedelta(minutes=30)
        ).time()
    )
    assert student_data.mid_school_arrival_time == time(12, 30)
    assert student_data.mid_stop_arrival_time == time(12, 45)


def test_update_stops_pm() -> None:
    """Test _update_stops with PM stops."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    student_data = StudentData(first_name="Alice", student_id="student1")
    stops = [
        MagicMock(
            time_of_day_id=coordinator.PM_ID,
            tier_start_time=time(15, 0),
            start_time=time(15, 15),
            stop_type="School",
            arrival_time=time(15, 30),
        ),
        MagicMock(
            time_of_day_id=coordinator.PM_ID,
            tier_start_time=time(15, 5),
            start_time=time(15, 20),
            stop_type="Stop",
            arrival_time=time(15, 45),
        ),
    ]
    coordinator._update_stops(student_data, stops)  # type: ignore This is magic mock
    assert student_data.pm_start_time == time(15, 0)
    assert (
        student_data.pm_end_time
        == (
            datetime.combine(dt_util.now().date(), time(15, 20)) + timedelta(minutes=30)
        ).time()
    )
    assert student_data.pm_school_arrival_time == time(15, 30)
    assert student_data.pm_stop_arrival_time == time(15, 45)


def test_is_am() -> None:
    """Test the _is_am method."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    assert coordinator._is_am(time(7, 0)) is True
    assert coordinator._is_am(time(10, 0)) is False
    assert coordinator._is_am(time(12, 0)) is False


def test_is_mid() -> None:
    """Test the _is_mid method."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    assert coordinator._is_mid(time(7, 0)) is False
    assert coordinator._is_mid(time(10, 0)) is True
    assert coordinator._is_mid(time(12, 0)) is True
    assert coordinator._is_mid(time(13, 30)) is False
    assert coordinator._is_mid(time(15, 0)) is False


def test_is_pm() -> None:
    """Test the _is_pm method."""
    coordinator = HCBDataCoordinator(
        hass=MagicMock(), config_entry=MagicMock(data={"update_interval": 20})
    )
    assert coordinator._is_pm(time(7, 0)) is False
    assert coordinator._is_pm(time(10, 0)) is False
    assert coordinator._is_pm(time(12, 0)) is False
    assert coordinator._is_pm(time(13, 30)) is True
    assert coordinator._is_pm(time(15, 0)) is True
    assert coordinator._is_pm(time(23, 59, 59)) is True


def test_student_is_moving_weekend(hass: HomeAssistant) -> None:
    """Test the _student_is_moving method on a weekend."""
    config_entry = MagicMock()
    config_entry.data = {CONF_UPDATE_INTERVAL: 30}
    config_entry.runtime_data = MagicMock(client=MagicMock())
    coordinator = HCBDataCoordinator(hass, config_entry)
    student_data = StudentData(
        first_name="Alice",
        student_id="student1",
        am_start_time=time(7, 0),
        am_end_time=time(8, 0),
        has_mid_stops=True,
        mid_start_time=time(11, 0),
        mid_end_time=time(12, 0),
        pm_start_time=time(15, 0),
        pm_end_time=time(16, 0),
    )

    # Calculate the number of days to shift to get the desired weekday (6 for Saturday)
    days_to_shift = (6 - dt_util.now().weekday()) % 7
    mock_datetime = dt_util.now() + timedelta(days=days_to_shift)

    with patch("homeassistant.util.dt.now", return_value=mock_datetime):  # Saturday
        assert not coordinator._student_is_moving(student_data)


def test_student_is_moving_am(hass: HomeAssistant) -> None:
    """Test the _student_is_moving method within AM time range."""
    config_entry = MagicMock()
    config_entry.data = {CONF_UPDATE_INTERVAL: 30}
    config_entry.runtime_data = MagicMock(client=MagicMock())
    coordinator = HCBDataCoordinator(hass, config_entry)
    student_data = StudentData(
        first_name="Alice",
        student_id="student1",
        am_start_time=time(7, 0),
        am_end_time=time(8, 0),
    )

    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=7, minute=30
        ),
    ):
        assert coordinator._student_is_moving(student_data)


def test_student_is_moving_mid(hass: HomeAssistant) -> None:
    """Test the _student_is_moving method within MID time range."""
    config_entry = MagicMock()
    config_entry.data = {CONF_UPDATE_INTERVAL: 30}
    config_entry.runtime_data = MagicMock(client=MagicMock())
    coordinator = HCBDataCoordinator(hass, config_entry)
    student_data = StudentData(
        first_name="Alice",
        student_id="student1",
        has_mid_stops=True,
        mid_start_time=time(11, 0),
        mid_end_time=time(12, 0),
    )

    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=11, minute=30
        ),
    ):
        assert coordinator._student_is_moving(student_data)


def test_student_is_moving_mid_no_mid_stops(hass: HomeAssistant) -> None:
    """Test the _student_is_moving method within MID time range."""
    config_entry = MagicMock()
    config_entry.data = {CONF_UPDATE_INTERVAL: 30}
    config_entry.runtime_data = MagicMock(client=MagicMock())
    coordinator = HCBDataCoordinator(hass, config_entry)
    student_data = StudentData(
        first_name="Alice",
        student_id="student1",
        has_mid_stops=False,
        mid_start_time=time(11, 0),
        mid_end_time=time(12, 0),
    )

    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=11, minute=30
        ),
    ):
        assert not coordinator._student_is_moving(student_data)


def test_student_is_moving_pm(hass: HomeAssistant) -> None:
    """Test the _student_is_moving method within PM time range."""
    config_entry = MagicMock()
    config_entry.data = {CONF_UPDATE_INTERVAL: 30}
    config_entry.runtime_data = MagicMock(client=MagicMock())
    coordinator = HCBDataCoordinator(hass, config_entry)
    student_data = StudentData(
        first_name="Alice",
        student_id="student1",
        pm_start_time=time(15, 0),
        pm_end_time=time(16, 0),
    )

    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=15, minute=30
        ),
    ):
        assert coordinator._student_is_moving(student_data)


def test_student_is_not_moving_outside_time_ranges(hass: HomeAssistant) -> None:
    """Test the _student_is_moving method outside of all time ranges."""
    config_entry = MagicMock()
    config_entry.data = {CONF_UPDATE_INTERVAL: 30}
    config_entry.runtime_data = MagicMock(client=MagicMock())
    coordinator = HCBDataCoordinator(hass, config_entry)
    student_data = StudentData(
        first_name="Alice",
        student_id="student1",
        am_start_time=time(7, 0),
        am_end_time=time(8, 0),
        has_mid_stops=True,
        mid_start_time=time(11, 0),
        mid_end_time=time(12, 0),
        pm_start_time=time(15, 0),
        pm_end_time=time(16, 0),
    )

    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(hour=9, minute=0),
    ):
        assert not coordinator._student_is_moving(student_data)


async def test_async_config_entry_first_refresh_initializes_school_and_parent_id(
    hass: HomeAssistant,
) -> None:
    """Test that async_config_entry_first_refresh inits school_id and parent_id."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }
    config_entry.runtime_data = MagicMock(client=MagicMock())  # Add a mock client
    coordinator = HCBDataCoordinator(hass, config_entry)

    # Mock the client methods (access through config_entry)
    config_entry.runtime_data.client.get_school_id = AsyncMock(return_value="school_id")
    config_entry.runtime_data.client.get_parent_info = AsyncMock(
        return_value=MagicMock(
            account_id="parent_id",
            students=[
                MagicMock(first_name="Alice", student_id="student1"),
                MagicMock(first_name="Bob", student_id="student2"),
            ],
            times=[
                MagicMock(id=coordinator.AM_ID),
                MagicMock(id=coordinator.MID_ID),
                MagicMock(id=coordinator.PM_ID),
            ],
        )
    )
    config_entry.runtime_data.client.get_stop_info = AsyncMock(
        return_value=MagicMock(
            vehicle_location=MagicMock(),
            student_stops=STUDENT_STOPS,
        )
    )

    await coordinator.async_config_entry_first_refresh()

    assert coordinator._school_id == "school_id"
    assert coordinator._parent_id == "parent_id"
    expected_student_count = 2
    assert len(coordinator.data) == expected_student_count


async def test_async_config_entry_first_refresh_updates_vehicle_location(
    hass: HomeAssistant,
) -> None:
    """Test that async_config_entry_first_refresh updates vehicle location."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }
    config_entry.runtime_data = MagicMock(client=MagicMock())  # Add a mock client
    coordinator = HCBDataCoordinator(hass, config_entry)

    # Mock the client methods (access through config_entry)
    config_entry.runtime_data.client.get_school_id = AsyncMock(return_value="school_id")
    config_entry.runtime_data.client.get_parent_info = AsyncMock(
        return_value=MagicMock(
            account_id="parent_id",
            students=[
                MagicMock(first_name="Alice", student_id="student1"),
                MagicMock(first_name="Bob", student_id="student2"),
            ],
            times=[
                MagicMock(id=coordinator.AM_ID),
                MagicMock(id=coordinator.MID_ID),
                MagicMock(id=coordinator.PM_ID),
            ],
        )
    )
    vehicle_location = MagicMock(
        address="123 Main St",
        display_on_map=True,
        heading="N",
        ignition=True,
        latent=False,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        log_time=dt_util.now(),
        message_code=1,
        speed=SPEED,
    )
    config_entry.runtime_data.client.get_stop_info = AsyncMock(
        return_value=MagicMock(
            vehicle_location=vehicle_location,
            student_stops=STUDENT_STOPS,
        )
    )

    await coordinator.async_config_entry_first_refresh()

    student_data = coordinator.data["student1"]
    assert student_data.address == "123 Main St"
    assert student_data.bus_name == vehicle_location.name
    assert student_data.display_on_map is True
    assert student_data.heading == "N"
    assert student_data.ignition is True
    assert student_data.latent is False
    assert student_data.latitude == LATITUDE
    assert student_data.longitude == LONGITUDE
    assert student_data.log_time == vehicle_location.log_time
    assert student_data.message_code == 1
    assert student_data.speed == SPEED


async def test_async_config_entry_first_refresh_handles_no_mid_stops(
    hass: HomeAssistant,
) -> None:
    """Test that async_config_entry_first_refresh handles no mid stops."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }
    config_entry.runtime_data = MagicMock(client=MagicMock())  # Add a mock client
    coordinator = HCBDataCoordinator(hass, config_entry)

    # Mock the client methods (access through config_entry)
    config_entry.runtime_data.client.get_school_id = AsyncMock(return_value="school_id")
    config_entry.runtime_data.client.get_parent_info = AsyncMock(
        return_value=MagicMock(
            account_id="parent_id",
            students=[
                MagicMock(first_name="Alice", student_id="student1"),
                MagicMock(first_name="Bob", student_id="student2"),
            ],
            times=[
                MagicMock(id=coordinator.AM_ID),
                MagicMock(id=coordinator.MID_ID),
                MagicMock(id=coordinator.PM_ID),
            ],
        )
    )
    config_entry.runtime_data.client.get_stop_info = AsyncMock(
        side_effect=[
            MagicMock(
                vehicle_location=MagicMock(),
                student_stops=STUDENT_STOPS,
            ),
            MagicMock(
                vehicle_location=MagicMock(),
                student_stops=[],
            ),
            MagicMock(
                vehicle_location=MagicMock(),
                student_stops=STUDENT_STOPS,
            ),
            MagicMock(
                vehicle_location=MagicMock(),
                student_stops=STUDENT_STOPS,
            ),
            MagicMock(
                vehicle_location=MagicMock(),
                student_stops=[],
            ),
            MagicMock(
                vehicle_location=MagicMock(),
                student_stops=STUDENT_STOPS,
            ),
        ]
    )

    await coordinator.async_config_entry_first_refresh()

    student_data = coordinator.data["student1"]
    assert student_data.has_mid_stops is False


async def test_async_config_entry_first_refresh_handles_no_stops_returned(
    hass: HomeAssistant,
) -> None:
    """Test that async_config_entry_first_refresh handles no mid stops."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }
    config_entry.runtime_data = MagicMock(client=MagicMock())  # Add a mock client
    coordinator = HCBDataCoordinator(hass, config_entry)

    # Mock the client methods (access through config_entry)
    config_entry.runtime_data.client.get_school_id = AsyncMock(return_value="school_id")
    config_entry.runtime_data.client.get_parent_info = AsyncMock(
        return_value=MagicMock(
            account_id="parent_id",
            students=[
                MagicMock(first_name="Alice", student_id="student1"),
                MagicMock(first_name="Bob", student_id="student2"),
            ],
            times=[
                MagicMock(id=coordinator.AM_ID),
                MagicMock(id=coordinator.MID_ID),
                MagicMock(id=coordinator.PM_ID),
            ],
        )
    )
    config_entry.runtime_data.client.get_stop_info = AsyncMock(
        side_effect=[
            MagicMock(
                vehicle_location=None,
                student_stops=[],
            ),
        ]
    )
    with pytest.raises(ValueError, match="No stops."):
        await coordinator.async_config_entry_first_refresh()


async def test_async_update_data_student_not_moving(hass: HomeAssistant) -> None:
    """Test the _async_update_data method when student is not moving."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }

    # Add a mock client to the config_entry
    config_entry.runtime_data = MagicMock(client=MagicMock())

    coordinator = HCBDataCoordinator(hass, config_entry)
    coordinator._school_id = "school_id"
    coordinator._parent_id = "parent_id"
    coordinator.data = {
        "student1": StudentData(
            first_name="Alice",
            student_id="student1",
        )
    }
    coordinator.data["student1"].am_start_time = time(7, 0)
    coordinator.data["student1"].am_end_time = time(8, 0)
    coordinator.data["student1"].has_mid_stops = True
    coordinator.data["student1"].mid_start_time = time(11, 0)
    coordinator.data["student1"].mid_end_time = time(12, 0)
    coordinator.data["student1"].pm_start_time = time(15, 0)
    coordinator.data["student1"].pm_end_time = time(16, 0)

    # Mock the client method (access through config_entry)
    config_entry.runtime_data.client.get_stop_info = AsyncMock()

    # Mock current time to be outside all ranges
    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(hour=9, minute=0),
    ):
        data = await coordinator._async_update_data()

    assert config_entry.runtime_data.client.get_stop_info.call_count == 0
    assert data == coordinator.data


async def test_async_update_data_student_moving(hass: HomeAssistant) -> None:
    """Test the _async_update_data method when student is moving."""
    config_entry = MagicMock()
    config_entry.data = {
        CONF_SCHOOL_CODE: "test_school",
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
    }

    # Add a mock client to the config_entry
    config_entry.runtime_data = MagicMock(client=MagicMock())

    coordinator = HCBDataCoordinator(hass, config_entry)
    coordinator._school_id = "school_id"
    coordinator._parent_id = "parent_id"
    coordinator.data = {
        "student1": StudentData(
            first_name="Alice",
            student_id="student1",
        )
    }
    coordinator.data["student1"].am_start_time = time(7, 0)
    coordinator.data["student1"].am_end_time = time(8, 0)
    coordinator.data["student1"].has_mid_stops = True
    coordinator.data["student1"].mid_start_time = time(11, 0)
    coordinator.data["student1"].mid_end_time = time(12, 0)
    coordinator.data["student1"].pm_start_time = time(15, 0)
    coordinator.data["student1"].pm_end_time = time(16, 0)

    # Mock the client method (access through config_entry)
    config_entry.runtime_data.client.get_stop_info = AsyncMock(
        return_value=MagicMock(
            vehicle_location=MagicMock(),
            student_stops=STUDENT_STOPS,
        )
    )

    # Mock current time to be within AM range
    with patch(
        "homeassistant.util.dt.now",
        return_value=dt_util.now().replace(
            month=10, day=31, year=2024, hour=7, minute=30
        ),
    ):
        data = await coordinator._async_update_data()

    assert config_entry.runtime_data.client.get_stop_info.call_count == 1
    assert data == coordinator.data
    assert coordinator.data["student1"].log_time is not None
