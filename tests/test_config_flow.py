"""Tests for config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.here_comes_the_bus import async_reload_entry
from custom_components.here_comes_the_bus.config_flow import HCBConfigFlowHandler
from custom_components.here_comes_the_bus.const import (
    CONF_ARRIVAL_ESTIMATES,
    CONF_DIRECTIONS,
    CONF_INFER_STOP,
    CONF_SCHOOL_CODE,
    CONF_STOP_ANNOUNCEMENTS,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from custom_components.here_comes_the_bus.data import StudentData

# Mock data
MOCK_USER_INPUT = {
    CONF_USERNAME: "test_username",
    CONF_PASSWORD: "test_password",
    CONF_SCHOOL_CODE: "test_school_code",
    CONF_UPDATE_INTERVAL: 20,
}


# This fixture is used to enable custom integrations, otherwise the custom_components
# folder will not be loaded.
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # noqa: ANN001, ANN201, ARG001
    """Enable custom integrations."""
    return


async def test_async_step_user_success(hass: HomeAssistant) -> None:
    """Test successful user step."""
    with patch(
        "custom_components.here_comes_the_bus.config_flow.HcbSoapClient"
    ) as mock_soap_client:
        # Mock the client instance and its methods
        mock_instance = AsyncMock()
        mock_instance.get_school_id = AsyncMock(return_value="test_school_id")
        mock_instance.get_parent_info = AsyncMock(
            return_value=MagicMock(account_id="test_account_id")
        )
        mock_soap_client.return_value = mock_instance

        with (
            patch(
                "custom_components.here_comes_the_bus.config_flow.HCBConfigFlowHandler.test_credentials",
                return_value=True,
            ),
            patch(
                "custom_components.here_comes_the_bus.async_setup_entry",
                new=AsyncMock(return_value=True),
            ),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )
            assert "type" in result
            assert "step_id" in result
            assert result["type"] == data_entry_flow.FlowResultType.FORM
            assert result["step_id"] == "user"

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input=MOCK_USER_INPUT
            )
            assert "type" in result
            assert "title" in result
            assert "data" in result
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert result["title"] == "Here Comes The Bus"
            assert result["data"] == MOCK_USER_INPUT


async def test_async_step_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test invalid authentication."""
    with patch(
        "custom_components.here_comes_the_bus.config_flow.HCBConfigFlowHandler.test_credentials",
        side_effect=InvalidAuth,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_INPUT
        )
        assert "type" in result
        assert "errors" in result
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_async_step_user_unknown_error(hass: HomeAssistant) -> None:
    """Test unknown error during authentication."""
    with patch(
        "custom_components.here_comes_the_bus.config_flow.HCBConfigFlowHandler.test_credentials",
        side_effect=Exception,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=MOCK_USER_INPUT
        )
        assert "type" in result
        assert "errors" in result
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_credentials() -> None:
    """Test the test_credentials method."""
    handler = HCBConfigFlowHandler()
    user_input = {
        "school_code": "test_school",
        "username": "test_user",
        "password": "test_password",
    }

    with patch(
        "custom_components.here_comes_the_bus.config_flow.HcbSoapClient"
    ) as mock_client:
        mock_client.return_value.get_school_id = AsyncMock(return_value="school_id")
        mock_client.return_value.get_parent_info = AsyncMock(
            return_value=MagicMock(account_id="account_id")
        )

        result = await handler.test_credentials(user_input)
        assert result is True

        mock_client.return_value.get_parent_info = AsyncMock(
            return_value=MagicMock(account_id="")
        )
        result = await handler.test_credentials(user_input)
        assert result is False


async def test_inferred_stop_options(hass: HomeAssistant) -> None:
    """Inference is opt-in and can be enabled through an existing entry's options."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_USER_INPUT)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["data_schema"]({}) == {
        CONF_ARRIVAL_ESTIMATES: True,
        CONF_INFER_STOP: False,
        CONF_STOP_ANNOUNCEMENTS: True,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_INFER_STOP: True}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_INFER_STOP] is True


async def test_per_student_direction_options(hass: HomeAssistant) -> None:
    """Changing one child's direction preserves other children and global options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_USER_INPUT,
        options={CONF_DIRECTIONS: {"other": {"am": "N", "pm": "S"}}},
    )
    entry.add_to_hass(hass)
    entry.runtime_data = MagicMock(
        coordinator=MagicMock(data={"s": StudentData("Alice", "s")})
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({})["student_id"] == ""
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_INFER_STOP: True,
            CONF_STOP_ANNOUNCEMENTS: True,
            "student_id": "s",
        },
    )
    assert result["step_id"] == "directions"
    assert result["data_schema"]({}) == {"am": "auto", "pm": "auto"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"am": "E", "pm": "W"}
    )
    assert entry.options[CONF_DIRECTIONS] == {
        "other": {"am": "N", "pm": "S"},
        "s": {"am": "E", "pm": "W"},
    }
    assert entry.options[CONF_INFER_STOP]


async def test_arrival_estimates_toggle_reloads_and_preserves_options(
    hass: HomeAssistant,
) -> None:
    """Disabling and re-enabling estimates reloads with other preferences intact."""
    directions = {"student1": {"am": "N", "pm": "S"}}
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_USER_INPUT,
        options={CONF_DIRECTIONS: directions, CONF_INFER_STOP: True},
    )
    entry.add_to_hass(hass)
    entry.add_update_listener(async_reload_entry)
    with patch.object(hass.config_entries, "async_reload", return_value=True) as reload:
        for enabled in (False, True):
            result = await hass.config_entries.options.async_init(entry.entry_id)
            assert result["data_schema"]({})[CONF_ARRIVAL_ESTIMATES] is not enabled
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], user_input={CONF_ARRIVAL_ESTIMATES: enabled}
            )
            await hass.async_block_till_done()
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert entry.options[CONF_ARRIVAL_ESTIMATES] is enabled
            assert entry.options[CONF_DIRECTIONS] == directions
            assert entry.options[CONF_INFER_STOP] is True
            reload.assert_awaited_once_with(entry.entry_id)
            reload.reset_mock()
