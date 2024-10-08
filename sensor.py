from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Student Sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [
        HCBSensor(coordinator, "Name"),
        HCBSensor(coordinator, "Latitude", "Latitude"),
        HCBSensor(coordinator, "Longitude", "Longitude"),
        HCBSensor(coordinator, "Address", "Address"),
        # Add any additional sensors you need here
    ]
    async_add_entities(sensors)


class HCBSensor(CoordinatorEntity, Entity):
    """Defines a single HCB sensor."""

    def __init__(self, coordinator, data_key, name):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.data_key = idx
        self._attr_name = ent["FirstName"]
        self._attr_unique_id = ent["StudentId"]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attr_name

    @property
    def unique_id(self):
        """Return a unique identifier for this sensor."""
        return self._attr_unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        # if self.data_key == "err":
        #     error = self.coordinator.data.get("err", 0)
        #     if error == 0:
        #         return "No"
        #     return "Yes"
        return self.coordinator.data.get(self.data_key, "Unknown")

  

    @property
    def device_info(self):
        """Return information about the device this sensor is part of."""
        return {
            "identifiers": "Here Comes The Bus",
            "name": "Here Comes The Bus",
            "manufacturer": "CalAmp Corp"
        }