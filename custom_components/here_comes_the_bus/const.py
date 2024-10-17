"""Constants for Here Comes the Bus custom component."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

__version__ = "0.0.1"
PROJECT_URL = "hhttps://github.com/moralmunky/Home-Assistant-Mail-And-Packages/"
ISSUE_URL = f"{PROJECT_URL}issues"

DOMAIN = "here_comes_the_bus"
HERE_COMES_THE_BUS = "Here comes the bus"
BUS = "Bus"

MIN_HA_MAJ_VER = 2024
MIN_HA_MIN_VER = 8
__min_ha_version__ = f"{MIN_HA_MAJ_VER}.{MIN_HA_MIN_VER}.0"

# configuration
CONF_SCHOOL_CODE = "school_code"
CONF_ADD_DEVICE_TRACKER = "add_device_tracker"
CONF_ADD_SENSORS = "add_sensors"
CONF_UPDATE_INTERVAL = "update_interval"


# general sensor attributes
ATTR_BUS_NAME = "bus_name"
ATTR_SPEED = "speed"
ATTR_MESSAGE_CODE = "message_code"
ATTR_DISPLAY_ON_MAP = "display_on_map"
ATTR_IGNITION = "ignition"
ATTR_LOG_TIME = "log_time"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_ADDRESS = "address"
ATTR_HEADING = "heading"
ATTR_AM_ARRIVAL_TIME = "am_arrival_time"
ATTR_PM_ARRIVAL_TIME = "pm_arrival_time"
