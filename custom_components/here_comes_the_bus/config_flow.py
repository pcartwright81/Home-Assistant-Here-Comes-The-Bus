"""Adds config flow for Here comes the bus."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from hcb_soap_client.hcb_soap_client import HcbSoapClient
from homeassistant import config_entries, data_entry_flow
from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, __version__

from . import is_valid_ha_version
from .const import (
    CONF_SCHOOL_CODE,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    HERE_COMES_THE_BUS,
    LOGGER,
    __min_ha_version__,
)

TITLE = HERE_COMES_THE_BUS
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SCHOOL_CODE): cv.string,
        vol.Optional(CONF_UPDATE_INTERVAL, default=20): cv.positive_int,
    }
)


class HCBConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Here Comes The Bus."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> data_entry_flow.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if not is_valid_ha_version():
            return self.async_abort(
                reason="unsupported_version",
                description_placeholders={
                    "req_ver": __min_ha_version__,
                    "run_ver": __version__,
                },
            )
        if user_input is not None:
            try:
                _ = await self.test_credentials(user_input)
            except InvalidAuth:
                _errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception")
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=TITLE,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=_errors,
        )

    async def test_credentials(self, user_input: dict) -> bool:
        """Validate credentials."""
        client = HcbSoapClient()
        return await client.test_connection(
            school_code=user_input[CONF_SCHOOL_CODE],
            user_name=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
        )
