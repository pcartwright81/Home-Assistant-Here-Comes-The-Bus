"""Test the init module."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.here_comes_the_bus import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
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
