"""
Custom integration to integrate Here comes the bus with Home Assistant.

For more details about this integration, please refer to
https://github.com/pcartwright81/Home-Assistant-Here-Comes-The-Bus
"""

from hcb_soap_client.hcb_soap_client import HcbSoapClient
from homeassistant.const import (
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_loaded_integration

from custom_components.here_comes_the_bus.coordinator import HCBDataCoordinator

from .data import HCBConfigEntry, HCBData

PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: HCBConfigEntry) -> bool:
    """Set up Here Comes the Bus integration from a config entry."""
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
