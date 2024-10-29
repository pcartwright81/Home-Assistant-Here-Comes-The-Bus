"""Test the init module."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION, Platform
from homeassistant.core import HomeAssistant

from custom_components.here_comes_the_bus import (
    _notify_message,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
    is_min_ha_version,
    is_valid_ha_version,
)
from custom_components.here_comes_the_bus.const import (
    DOMAIN,
)


@pytest.fixture(autouse=True)
def skip_first_refresh() -> Generator:
    """Skip the first refresh."""
    with patch(
        "custom_components.here_comes_the_bus.coordinator.HCBDataCoordinator.async_config_entry_first_refresh",
        return_value=None,
    ):
        yield


async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test the async_setup_entry function."""
    entry = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    entry.add_update_listener = MagicMock()

    with (
        patch(
            "custom_components.here_comes_the_bus.is_valid_ha_version",
            return_value=True,
        ),
        patch(
            "custom_components.here_comes_the_bus.HCBDataCoordinator"
        ) as mock_coordinator,
        patch(
            "custom_components.here_comes_the_bus.async_get_loaded_integration"
        ) as mock_get_loaded_integration,
        patch("custom_components.here_comes_the_bus.HcbSoapClient") as mock_client,
    ):
        # Mock the client methods
        mock_client.return_value.get_school_id = AsyncMock(return_value="school_id")
        mock_client.return_value.get_parent_info = AsyncMock(
            return_value=MagicMock(
                account_id="parent_id",
                students=[
                    MagicMock(first_name="Alice", student_id="student1"),
                    MagicMock(first_name="Bob", student_id="student2"),
                ],
                times=[
                    MagicMock(id="55632A13-35C5-4169-B872-F5ABDC25DF6A"),
                    MagicMock(id="27AADCA0-6D7E-4247-A80F-7847C448EEED"),
                    MagicMock(id="6E7A050E-0295-4200-8EDC-3611BB5DE1C1"),
                ],
            )
        )
        mock_client.return_value.get_stop_info = AsyncMock(
            return_value=MagicMock(
                vehicle_location=MagicMock(),
                student_stops=[
                    MagicMock(stop_type="School"),
                    MagicMock(stop_type="Stop"),
                ],
            )
        )
        mock_coordinator.return_value.async_config_entry_first_refresh = AsyncMock()
        mock_get_loaded_integration.return_value = MagicMock()
        result = await async_setup_entry(hass, entry)
        assert result is True
        mock_coordinator.return_value.async_config_entry_first_refresh.assert_called_once()
        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            entry, [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]
        )
        entry.add_update_listener.assert_called_once_with(async_reload_entry)


async def test_async_setup_entry_invalid_ha_version(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test async_setup_entry with invalid Home Assistant version."""
    entry = MagicMock()
    with patch(
        "custom_components.here_comes_the_bus.is_valid_ha_version",
        return_value=False,
    ):
        result = await async_setup_entry(hass, entry)
        assert result is False
        assert "This integration requires at least HomeAssistant version" in caplog.text


def test_is_min_ha_version() -> None:
    """Test is_min_ha_version function."""
    # Test with current version
    assert is_min_ha_version(MAJOR_VERSION, MINOR_VERSION) is True

    # Test with older major version
    assert is_min_ha_version(MAJOR_VERSION - 1, MINOR_VERSION) is True

    # Test with older minor version
    assert is_min_ha_version(MAJOR_VERSION, MINOR_VERSION - 1) is True

    # Test with newer major version
    assert is_min_ha_version(MAJOR_VERSION + 1, MINOR_VERSION) is False

    # Test with newer minor version
    assert is_min_ha_version(MAJOR_VERSION, MINOR_VERSION + 1) is False


def test_is_valid_ha_version() -> None:
    """Test the is_valid_ha_version function."""
    with patch(
        "custom_components.here_comes_the_bus.is_min_ha_version", return_value=True
    ):
        assert is_valid_ha_version() is True
    with patch(
        "custom_components.here_comes_the_bus.is_min_ha_version",
        return_value=False,
    ):
        assert is_valid_ha_version() is False


async def test_notify_message(hass: HomeAssistant) -> None:
    """Test the _notify_message function."""
    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as mock_create:
        _notify_message(hass, "test_id", "Test Title", "Test Message")
        mock_create.assert_called_once_with(
            hass, "Test Message", "Test Title", f"{DOMAIN}.test_id"
        )


async def test_async_unload_entry(hass: HomeAssistant) -> None:
    """Test the async_unload_entry function."""
    entry = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    result = await async_unload_entry(hass, entry)
    assert result is True
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(
        entry, [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]
    )


async def test_async_reload_entry(hass: HomeAssistant) -> None:
    """Test the async_reload_entry function."""
    entry = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    await async_reload_entry(hass, entry)
    hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)
