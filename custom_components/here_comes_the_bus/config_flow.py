"""Config file for Here comes the bus Home assistant integration."""

import logging
from typing import Any

from hcb_soap_client import HcbSoapClient
import voluptuous as vol

from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, __version__
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from . import is_valid_ha_version
from .const import (
    CONF_ADD_DEVICE_TRACKER,
    CONF_ADD_SENSORS,
    CONF_SCHOOL_CODE,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    HERE_COMES_THE_BUS,
    __min_ha_version__,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SCHOOL_CODE): cv.string,
        vol.Optional(CONF_ADD_DEVICE_TRACKER, default=True): cv.boolean,
        vol.Optional(CONF_ADD_SENSORS, default=True): cv.boolean,
        vol.Optional(CONF_UPDATE_INTERVAL, default=20): cv.positive_int,
    }
)


async def validate_input(_: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.
    valid = await HcbSoapClient.test_connection(
        data[CONF_SCHOOL_CODE],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )
    if not valid:
        # If there is an error, raise an exception to notify HA that there was a
        # problem. The UI will also show there was a problem
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    # "Title" is what is displayed to the user for this hub device
    # It is stored internally in HA as part of the device config.
    # See `async_step_user` below for how this is used
    return {"title": HERE_COMES_THE_BUS}


class HCBConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Here Comes The Bus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if not is_valid_ha_version():
            return self.async_abort(
                reason="unsupported_version",
                description_placeholders={
                    "req_ver": __min_ha_version__,
                    "run_ver": __version__,
                },
            )
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["title"], data=user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
