"""
Custom integration to integrate Here comes the bus with Home Assistant.

For more details about this integration, please refer to
https://github.com/pcartwright81/Home-Assistant-Here-Comes-The-Bus
"""

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
from homeassistant.loader import async_get_loaded_integration

from custom_components.here_comes_the_bus.coordinator import HCBDataCoordinator

from .const import (
    CONF_SCHOOL_CODE,
    DOMAIN,
    HERE_COMES_THE_BUS,
    LOGGER,
    MIN_HA_MAJ_VER,
    MIN_HA_MIN_VER,
    __min_ha_version__,
)
from .data import HCBConfigEntry, HCBData

PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: HCBConfigEntry) -> bool:
    """Set up Here Comes the Bus integration from a config entry."""
    if not is_valid_ha_version():
        msg = (
            "This integration require at least HomeAssistant version "
            f" {__min_ha_version__}, you are running version {__version__}."
            " Please upgrade HomeAssistant to continue use this integration."
        )
        _notify_message(hass, "inv_ha_version", HERE_COMES_THE_BUS, msg)
        LOGGER.warning(msg)
        return False
    _fix_config(hass, entry)
    coordinator = HCBDataCoordinator(hass, entry)
    entry.runtime_data = HCBData(
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def is_min_ha_version(min_ha_major_ver: int, min_ha_minor_ver: int) -> bool:
    """Check if HA version at least a specific version."""
    return min_ha_major_ver < MAJOR_VERSION or (
        min_ha_major_ver == MAJOR_VERSION and min_ha_minor_ver <= MINOR_VERSION
    )


def is_valid_ha_version() -> bool:
    """Check if HA version is valid for this integration."""
    return is_min_ha_version(MIN_HA_MAJ_VER, MIN_HA_MIN_VER)


def format_message_code(message_code: int | None) -> str | None:
    """Format the message code to a string value."""
    if message_code == 0:
        return "In Service"
    if message_code is None or message_code == 2:  # noqa: PLR2004 fix this later
        return "Out Of Service"
    LOGGER.error("Message code was %s", message_code)
    return str(message_code)


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


async def async_unload_entry(
    hass: HomeAssistant,
    entry: HCBConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: HCBConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
