from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import datetime, timedelta
import logging
from .const import DOMAIN
from .hcbapi.hcbapi import GetUserInfo, GetSchoolInfo, GetBusLocation, AM_ID, PM_ID

PLATFORMS = [Platform.DEVICE_TRACKER]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = HCBDataCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    )
    return True


class HCBDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config):
        self.config = config
        self.schoolId = None
        self.parentId = None
        self.studentId = None
        self.students = None
        self.initialized = 0
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=15)
        )

    async def _async_update_data(self):
        data = await self.fetch_data()
        if data is None:
            raise UpdateFailed("Failed to fetch data from Here Comes the Bus.")
        return data

    async def fetch_data(self):
        if(self.schoolId is None):
             school = await GetSchoolInfo(self.config["SchoolCode"])
             self.schoolId = school.customer.id

        if(self.parentId is None):
            userInfo = await GetUserInfo(
                self.schoolId, self.config["Username"], self.config["Password"]
            )
            self.parentId = userInfo.account.id
            self.students = userInfo.linked_students.student

        nw = datetime.now()
        timeofDayId = AM_ID
        if(nw.hour > 12):
            timeofDayId = PM_ID

        if(self.initialized):
            if(nw.hour < 5):
                return []
            if(nw.hour > 8 and nw.hour < 14):
                return []
            if(nw.hour > 16):
                return []

        messages = []
        for student in self.students:
            stops = await GetBusLocation(self.schoolId, self.parentId, student.entity_id, timeofDayId)
            vehicleLocation = stops.vehicle_location
            newMessage = {
                "StudentId": student.entity_id,
                "StudentName": student.first_name,
                "Status": vehicleLocation.message_code,
                "Address": vehicleLocation.address,
                "Latitude": vehicleLocation.longitude,
                "Longitude": vehicleLocation.latitude,
                "BusName": vehicleLocation.name,
            }
            messages.append(newMessage)
        self.initialized = 1
        return messages


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
