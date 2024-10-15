"""Config file for Here comes the bus Home assistant integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .defaults import Defaults
from .hcbapi import hcbapi

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(Defaults.USERNAME): cv.string,
        vol.Required(Defaults.PASSWORD): cv.string,
        vol.Required(Defaults.SCHOOL_CODE): cv.string,
        vol.Optional(Defaults.ADD_DEVICE_TRACKER, default=True): cv.boolean,
        vol.Optional(Defaults.ADD_SENSORS, default=True): cv.boolean,
        vol.Optional(Defaults.UPDATE_INTERVAL, default=20): cv.positive_int,
    }
)


async def validate_input(_: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.
    valid = await hcbapi.test_connection(
        data[Defaults.SCHOOL_CODE],
        data[Defaults.USERNAME],
        data[Defaults.PASSWORD],        
    )
    if not valid:
        # If there is an error, raise an exception to notify HA that there was a
        # problem. The UI will also show there was a problem
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    # "Title" is what is displayed to the user for this hub device
    # It is stored internally in HA as part of the device config.
    # See `async_step_user` below for how this is used
    return {"title": Defaults.HERE_COMES_THE_BUS}


class ConfigFlow(config_entries.ConfigFlow, domain=Defaults.DOMAIN):
    """Handle a config flow for Here Comes The Bus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # This goes through the steps to take the user through the setup process.
        # Using this it is possible to update the UI and prompt for additional
        # information. This example provides a single form (built from `DATA_SCHEMA`),
        # and when that has some validated input, it calls `async_create_entry` to
        # actually create the HA config entry. Note the "title" value is returned by
        # `validate_input` above.
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
