"""Define a device tracker."""

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DataUpdateEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up bus sensors."""
    coordinator = hass.data[entry.entry_id]
    async_add_entities(
        HCBTracker(coordinator, idx, ent) for idx, ent in enumerate(coordinator.data)
    )


class HCBTracker(CoordinatorEntity, TrackerEntity):
    """Defines a single bus sensor."""

    def __init__(self, coordinator, idx, data: DataUpdateEntity) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.name = data.student.first_name + " Bus"
        self.idx = idx
        self.unique_id = data.student.first_name.lower() + "_bus"
        self._attr_bus_name: str
        self._update_atributes(data)

    def _update_atributes(self, data):
        if data.vehiclelocation is not None:
            self._attr_latitude = data.vehiclelocation.latitude
            self._attr_longitude = data.vehiclelocation.longitude
            self._attr_bus_name = data.vehiclelocation.name

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        data = self.coordinator.data[self.idx]
        self._update_atributes(data)
        self.async_write_ha_state()
