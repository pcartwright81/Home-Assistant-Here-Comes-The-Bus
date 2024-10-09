from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from homeassistant.core import callback


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Student Sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HCBTracker(coordinator, idx, ent) for idx, ent in enumerate(coordinator.data)
    )


# todo data keys should be an id, but it will not let me
class HCBTracker(CoordinatorEntity, TrackerEntity):
    """Defines a single HCB sensor."""

    def __init__(self, coordinator, idx, student):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self._student = student
        self.idx = idx

    @property
    def latitude(self):
        return self._student["Latitude"]

    @property
    def longitude(self):
        return self._student["Longitude"]

    @property
    def location_name(self):
        return self._student["Address"]

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._student["StudentName"].lower() + "_bus"

    @property
    def name(self):
        """Return the name."""
        return self._student["StudentName"] + " Bus"

    @property
    def status(self):
        """Return the name."""
        return self._student["Status"]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._student = self.coordinator.data[self.idx]
        self.async_write_ha_state()
