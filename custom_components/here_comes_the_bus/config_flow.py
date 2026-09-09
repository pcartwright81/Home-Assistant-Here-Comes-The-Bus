"""Adds config flow for Here comes the bus."""

from __future__ import annotations

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from hcb_soap_client.hcb_soap_client import HcbSoapClient
from homeassistant import config_entries
from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .const import (
    CONF_DIRECTIONS,
    CONF_SCHOOL_CODE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ETA_OPTIONS,
    DOMAIN,
    HERE_COMES_THE_BUS,
    LOGGER,
)

DIRECTION_CHOICES = {
    "auto": "Automatic",
    "N": "North",
    "NE": "Northeast",
    "E": "East",
    "SE": "Southeast",
    "S": "South",
    "SW": "Southwest",
    "W": "West",
    "NW": "Northwest",
}

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

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> HCBOptionsFlow:
        """Offer arrival estimate settings."""
        return HCBOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
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
        school_id = await client.get_school_id(user_input[CONF_SCHOOL_CODE])
        account_info = await client.get_parent_info(
            school_id=school_id,
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
        )
        return account_info.account_id != ""


class HCBOptionsFlow(config_entries.OptionsFlow):
    """Configure arrival estimates and announcement controls."""

    def __init__(self) -> None:
        """Keep pending options local until all requested steps are complete."""
        self._options: dict = {}
        self._student_id = ""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure independent completion and announcement controls."""
        if user_input is not None:
            self._options = {**self.config_entry.options, **user_input}
            self._student_id = self._options.pop("student_id", "")
            if self._student_id:
                return await self.async_step_directions()
            return self.async_create_entry(title="", data=self._options)
        schema = {
            vol.Optional(
                key, default=self.config_entry.options.get(key, default)
            ): cv.boolean
            for key, default in DEFAULT_ETA_OPTIONS.items()
        }
        runtime = getattr(self.config_entry, "runtime_data", None)
        students = getattr(getattr(runtime, "coordinator", None), "data", {})
        if students:
            schema[vol.Optional("student_id", default="")] = vol.In(
                {
                    "": "No changes",
                    **{
                        student.student_id: student.first_name
                        for student in students.values()
                    },
                }
            )
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))

    async def async_step_directions(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Set separate AM and PM approach directions for the selected student."""
        if user_input is not None:
            directions = {
                **self._options.get(CONF_DIRECTIONS, {}),
                self._student_id: user_input,
            }
            return self.async_create_entry(
                title="", data={**self._options, CONF_DIRECTIONS: directions}
            )
        current = self._options.get(CONF_DIRECTIONS, {}).get(self._student_id, {})
        return self.async_show_form(
            step_id="directions",
            data_schema=vol.Schema(
                {
                    vol.Optional(period, default=current.get(period, "auto")): vol.In(
                        DIRECTION_CHOICES
                    )
                    for period in ("am", "pm")
                }
            ),
        )
