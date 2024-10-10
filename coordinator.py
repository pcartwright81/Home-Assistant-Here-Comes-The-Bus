from .hcbapi.hcbapi import GetUserInfo, GetSchoolInfo, GetBusLocation, AM_ID, PM_ID
from .const import DOMAIN
from datetime import datetime, timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


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

    async def _async_setup(self):
        school = await GetSchoolInfo(self.config["SchoolCode"])
        self.schoolId = school.customer.id
        userInfo = await GetUserInfo(
            self.schoolId, self.config["Username"], self.config["Password"]
        )
        self.parentId = userInfo.account.id
        self.students = userInfo.linked_students.student

    async def _async_update_data(self):
        data = await self.fetch_data()
        if data is None:
            raise UpdateFailed("Failed to fetch data from Here Comes the Bus.")
        return data

    async def fetch_data(self):
        nw = datetime.now()
        timeofDayId = AM_ID
        if nw.hour > 12:
            timeofDayId = PM_ID

        if self.initialized:
            if nw.hour < 5:
                return []
            if nw.hour > 8 and nw.hour < 14:
                return []
            if nw.hour > 16:
                return []

        messages = []
        for student in self.students:
            stops = await GetBusLocation(
                self.schoolId, self.parentId, student.entity_id, timeofDayId
            )
            vehicleLocation = stops.vehicle_location
            newMessage = {
                "StudentId": student.entity_id,
                "StudentName": student.first_name,
                "Status": None,
                "Address": None,
                "Latitude": None,
                "Longitude": None,
                "DisplayOnMap": None,
                "BusName": None,
            }
            if vehicleLocation is not None:
                newMessage["Status"] = vehicleLocation.message_code
                newMessage["Address"] = vehicleLocation.address
                newMessage["Latitude"] = vehicleLocation.latitude
                newMessage["Longitude"] = vehicleLocation.longitude
                newMessage["DisplayOnMap"] = vehicleLocation.display_on_map
                newMessage["BusName"] = vehicleLocation.name
            messages.append(newMessage)
        self.initialized = 1
        return messages
