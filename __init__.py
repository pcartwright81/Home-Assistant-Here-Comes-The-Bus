from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta
import logging
from .const import DOMAIN
from .hcb_api import GetUserInfo, GetSchoolInfo, GetBusLocation

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = HCBDataCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True


class HCBDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        self.config = config
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=30)
        )

    async def _async_update_data(self):
        data = await self.fetch_data()
        if data is None:
            raise UpdateFailed("Failed to fetch data from Here Comes the Bus.")
        return data

    async def fetch_data(self):
        school = await GetSchoolInfo(self.config["SchoolCode"])
        schoolId = school["Id"]
        userInfo = await GetUserInfo(
            schoolId, self.config["Username"], self.config["Password"]
        )
        parentId = userInfo["ParentId"]
        messages = []
        for student in userInfo["Students"]:
            studentId = student["StudentId"]
            firstName = student["FirstName"]
            vechicleLocation = await GetBusLocation(schoolId, parentId, studentId)
            newMessage = {
                "StudentId": studentId,
                "FirstName": firstName,
                "Status": vechicleLocation["Status"],
                "Address": vechicleLocation["Address"],
                "Latitude": vechicleLocation["Latitude"],
                "Longitude": vechicleLocation["Longitude"],
                "Name": vechicleLocation["Name"],
            }
            messages.append(newMessage)
        return messages
