"""Config file for Here comes the bus Home assistant integration."""

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .hcbapi.hcbapi import get_parent_info, get_school_info


class HereComesTheBusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Here Comes The Bus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            valid = await self._test_connection(
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
                }
            ),
            errors=errors,
        )

    async def _test_connection(self, username, password, school_code):
        """Test connection to the Here Comes the Bus."""
        try:
            school = await get_school_info(school_code)
            school_id = school.customer.id
            userInfo = await get_parent_info(school_id, username, password)
        except Exception:  # noqa: BLE001 don't feel like changing this
            return None  # Unable to connect
        else:
             return userInfo is not None
