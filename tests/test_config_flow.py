"""Tests for config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.here_comes_the_bus.config_flow import HCBConfigFlowHandler
from custom_components.here_comes_the_bus.const import (
    CONF_SCHOOL_CODE,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)

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
        "custom_components.here_comes_the_bus.config_flow.HCBConfigFlowHandler.test_credentials",
        return_value=True,
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
