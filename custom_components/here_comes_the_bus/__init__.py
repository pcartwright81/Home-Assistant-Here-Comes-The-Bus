"""
Custom integration to integrate Here comes the bus with Home Assistant.

For more details about this integration, please refer to
https://github.com/pcartwright81/Home-Assistant-Here-Comes-The-Bus
"""

from hcb_soap_client.hcb_soap_client import HcbSoapClient
from homeassistant.components import persistent_notification
from homeassistant.const import (
    MAJOR_VERSION,
    MINOR_VERSION,
    Platform,
    __version__,
)
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_loaded_integration

from custom_components.here_comes_the_bus.coordinator import HCBDataCoordinator

from .const import (
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
            "This integration requires at least HomeAssistant version "
            f"{__min_ha_version__}, you are running version {__version__}. "
            "Please upgrade HomeAssistant to continue use this integration."
        )
        _notify_message(hass, "inv_ha_version", HERE_COMES_THE_BUS, msg)
        LOGGER.warning(msg)
        return False
    coordinator = HCBDataCoordinator(hass, entry)
    entry.runtime_data = HCBData(
        client=HcbSoapClient(),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


def is_min_ha_version(min_ha_major_ver: int, min_ha_minor_ver: int) -> bool:
    """Check if HA version at least a specific version."""
    return min_ha_major_ver < MAJOR_VERSION or (
        min_ha_major_ver == MAJOR_VERSION and min_ha_minor_ver <= MINOR_VERSION
    )


def is_valid_ha_version() -> bool:
    """Check if HA version is valid for this integration."""
    return is_min_ha_version(MIN_HA_MAJ_VER, MIN_HA_MIN_VER)


def _notify_message(
    hass: HomeAssistant, notification_id: str, title: str, message: str
) -> None:
    """Notify user with persistent notification."""
    persistent_notification.async_create(
        hass, message, title, f"{DOMAIN}.{notification_id}"
    )


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
    await hass.config_entries.async_reload(entry.entry_id)
