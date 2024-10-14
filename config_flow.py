"""Config file for Here comes the bus Home assistant integration."""

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from .const import Const
from .hcbapi import hcbapi


class HereComesTheBusConfigFlow(config_entries.ConfigFlow, domain=Const.DOMAIN):
    """Handle a config flow for Here Comes The Bus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            valid = await hcbapi.test_connection(
                user_input["Username"], user_input["Password"], user_input["SchoolCode"]
            )
            if valid:
                return self.async_create_entry(
                    title="Here Comes The Bus", data=user_input
                )
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("Username"): cv.string,
                    vol.Required("Password"): cv.string,
                    vol.Required("SchoolCode"): cv.string,
                    vol.Optional("AddDeviceTracker", default=True): cv.boolean,
                    vol.Optional("AddSensors", default=True): cv.boolean,
                    vol.Optional("UpdateInterval", default=20): cv.positive_int,
                }
            ),
            errors=errors,
        )
