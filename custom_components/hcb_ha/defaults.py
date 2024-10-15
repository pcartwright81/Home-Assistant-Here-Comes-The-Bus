"""Default properties and methods."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .student_data import StudentData


class Defaults:
    """Default properties and methods."""

    DOMAIN = "hcb_ha"
    ATTR_BUS_NAME = "Number"
    ATTR_SPEED = "Speed"
    ATTR_MESSAGE_CODE = "Message Code"
    ATTR_DISPLAY_ON_MAP = "Display On Map"
    ATTR_IGNITION = "Ignition On"
    ATTR_LOG_TIME = "Last Seen"
    ATTR_LATITUDE = "Latitude"
    ATTR_LONGITUDE = "Longitude"
    ATTR_ADDRESS = "Address"
    ATTR_HEADING = "Heading"
    ATTR_AM_SCHOOL_ARRIVAL_TIME = "AM School Arrival Time"
    ATTR_PM_STOP_ARRIVAL_TIME = "PM Stop Arrival Time"
    HERE_COMES_THE_BUS = "Here comes the bus"
    BUS = "Bus"
    USERNAME = "Username"
    PASSWORD = "Password"
    SCHOOL_CODE = "SchoolCode"
    ADD_DEVICE_TRACKER = "AddDeviceTracker"
    ADD_SENSORS = "AddSensors"
    UPDATE_INTERVAL = "UpdateInterval"

    def get_device_info(self, student_data: StudentData):
        """Get the standard device info."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(Defaults.DOMAIN, student_data.student_id)},
            manufacturer=Defaults.HERE_COMES_THE_BUS,
            name=f"{student_data.first_name} {Defaults.BUS}",
        )
