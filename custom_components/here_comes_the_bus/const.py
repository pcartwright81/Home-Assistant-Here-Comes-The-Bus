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

# configuration
CONF_SCHOOL_CODE = "school_code"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_INFER_STOP = "infer_stop_visits"
CONF_STOP_ANNOUNCEMENTS = "stop_announcements_after_pass"
CONF_DIRECTIONS = "stop_directions"
CONF_ARRIVAL_ESTIMATES = "arrival_estimates"

DEFAULT_ETA_OPTIONS = {
    CONF_ARRIVAL_ESTIMATES: True,
    CONF_INFER_STOP: False,
    CONF_STOP_ANNOUNCEMENTS: True,
}
ETA_ENTITY_KEYS = frozenset(
    {
        "stop_eta",
        "eta_status",
        "eta_details",
        "stop_visit_inferred",
        "eta_announcements_allowed",
    }
)
