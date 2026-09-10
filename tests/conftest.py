"""Pytest configuration and fixtures for tests."""

from collections.abc import Awaitable, Callable, Generator
from typing import cast
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

type SetupComponent = Callable[
    [HomeAssistant, str, dict[str, object] | None],
    Awaitable[bool],
]


@pytest.fixture(autouse=True)
def mock_recorder() -> Generator[None, None, None]:
    """
    Mock the recorder component to prevent initialization errors.

    The recorder component has a circular dependency issue during testing.
    This fixture prevents the recorder from being loaded and set up during tests.
    """
    with (
        patch("homeassistant.setup.async_setup_component") as mock_setup,
    ):
        original_setup = mock_setup.side_effect

        async def setup_component_with_recorder_mock(
            hass: HomeAssistant,
            domain: str,
            config: dict[str, object] | None,
        ) -> bool:
            """Set up the component while mocking the recorder."""
            if domain == "recorder":
                return True
            # Call the original or default behavior for other domains
            if callable(original_setup):
                return await cast(
                    "SetupComponent",
                    original_setup,
                )(hass, domain, config)
            return True

        mock_setup.side_effect = setup_component_with_recorder_mock
        yield
