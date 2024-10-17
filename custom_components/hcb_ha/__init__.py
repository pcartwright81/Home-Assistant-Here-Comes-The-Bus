"""Init file for Here comes the bus Home assistant integration."""

import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    MAJOR_VERSION,
    MINOR_VERSION,
    Platform,
    __version__,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import (
    BUS,
    CONF_SCHOOL_CODE,
    DOMAIN,
    HERE_COMES_THE_BUS,
    MIN_HA_MAJ_VER,
    MIN_HA_MIN_VER,
    __min_ha_version__,
)
from .coordinator import HCBDataCoordinator
from .student_data import StudentData

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Here Comes the Bus integration from a config entry."""
    if not is_valid_ha_version():
        msg = (
            "This integration require at least HomeAssistant version "
            f" {__min_ha_version__}, you are running version {__version__}."
            " Please upgrade HomeAssistant to continue use this integration."
        )
        _notify_message(hass, "inv_ha_version", HERE_COMES_THE_BUS, msg)
        _LOGGER.warning(msg)
        return False
    _fix_config(hass, entry)
    coordinator = HCBDataCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def is_min_ha_version(min_ha_major_ver: int, min_ha_minor_ver: int) -> bool:
    """Check if HA version at least a specific version."""
    return min_ha_major_ver < MAJOR_VERSION or (
        min_ha_major_ver == MAJOR_VERSION and min_ha_minor_ver <= MINOR_VERSION
    )


def is_valid_ha_version() -> bool:
    """Check if HA version is valid for this integration."""
    return is_min_ha_version(MIN_HA_MAJ_VER, MIN_HA_MIN_VER)


def get_device_info(student_data: StudentData):
    """Get the standard device info."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, student_data.student_id)},
        manufacturer=HERE_COMES_THE_BUS,
        name=f"{student_data.first_name} {BUS}",
    )


def _notify_message(
    hass: HomeAssistant, notification_id: str, title: str, message: str
) -> None:
    """Notify user with persistent notification."""
    persistent_notification.async_create(
        hass, message, title, f"{DOMAIN}.{notification_id}"
    )


@callback
def _fix_config(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate an old config entry if available."""
    if "Username" not in entry.data:
        return
    new_data = {}
    new_data[CONF_USERNAME] = entry.data[CONF_USERNAME.title()]
    new_data[CONF_PASSWORD] = entry.data[CONF_PASSWORD.title()]
    new_data[CONF_SCHOOL_CODE] = entry.data["SchoolCode"]
    hass.config_entries.async_update_entry(entry, data=new_data)
