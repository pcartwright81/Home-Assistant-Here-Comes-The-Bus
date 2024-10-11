"""Define a device tracker."""

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import DataUpdateEntity, HCBDataCoordinator


async def async_setup_entry(_: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up bus sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        HCBTracker(coordinator, idx, ent) for idx, ent in enumerate(coordinator.data)
    )


class HCBTracker(CoordinatorEntity, TrackerEntity):
    """Defines a single bus sensor."""

    def __init__(
        self, coordinator: HCBDataCoordinator, idx: int, ent: DataUpdateEntity
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx
        self.name = ent.student.first_name + " Bus"
        self.unique_id = ent.student.first_name.lower() + "_bus"
        self._attr_bus_name: str
        self._update_atributes(ent)

    def _update_atributes(self, ent: DataUpdateEntity):
        if ent.vehiclelocation is not None:
            self._attr_latitude = ent.vehiclelocation.latitude
            self._attr_longitude = ent.vehiclelocation.longitude
            self._attr_bus_name = ent.vehiclelocation.name

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None: # this is expected because we are not calling all the time
            return
        ent = self.coordinator.data[self.idx]
        self._update_atributes(ent)
        self.async_write_ha_state()
