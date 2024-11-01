"""Constants for Here Comes the Bus custom component."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

__version__ = "0.0.9"
PROJECT_URL = "https://github.com/pcartwright81/Home-Assistant-Here-Comes-The-Bus/"
ISSUE_URL = f"{PROJECT_URL}issues"

DOMAIN = "here_comes_the_bus"
HERE_COMES_THE_BUS = "Here Comes The Bus"
BUS = "Bus"
HMS = "%H:%M:%S"
MIN_HA_MAJ_VER = 2024
MIN_HA_MIN_VER = 10
__min_ha_version__ = f"{MIN_HA_MAJ_VER}.{MIN_HA_MIN_VER}.0"

# configuration
CONF_SCHOOL_CODE = "school_code"
CONF_UPDATE_INTERVAL = "update_interval"
