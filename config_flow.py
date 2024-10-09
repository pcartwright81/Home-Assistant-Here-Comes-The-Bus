import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .hcbapi.hcbapi import GetSchoolInfo, GetUserInfo
from .const import DOMAIN


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
            else:
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

    async def _test_connection(self, username, password, schoolcode):
        """Test connection to the Here Comes the Bus."""
        try:
            school = await GetSchoolInfo(schoolcode)
            schoolId = school.customer.id
            userInfo = await GetUserInfo(schoolId, username, password)
            _ = userInfo.account.id #the call failed and the data does not exist
            return True
        except Exception as e:
            return None  # Unable to connect
