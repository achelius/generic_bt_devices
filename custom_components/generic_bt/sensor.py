"""Support for Generic BT sensor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CHARACTERISTIC_READERS, CONF_CHARACTERISTIC_NAME, CONF_TARGET_UUID
from .coordinator import GenericBTCoordinator
from .entity import GenericBTEntity

# Initialize the logger
_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Generic BT sensor based on a config entry."""
    coordinator: GenericBTCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    characteristics = entry.options.get(CONF_CHARACTERISTIC_READERS, [])
    
    for characteristic in characteristics:
        entities.append(
            GenericBTCharacteristicSensor(
                coordinator=coordinator,
                name=characteristic.get(CONF_CHARACTERISTIC_NAME),
                target_uuid=characteristic.get(CONF_TARGET_UUID)
            )
        )
    
    if entities:
        async_add_entities(entities)


class GenericBTCharacteristicSensor(GenericBTEntity, SensorEntity):
    """Representation of a Generic BT Characteristic Sensor."""

    def __init__(
        self,
        coordinator: GenericBTCoordinator,
        name: str,
        target_uuid: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = name
        self._target_uuid = target_uuid
        self._attr_unique_id = f"{coordinator.base_unique_id}_{target_uuid}"
        self._attr_native_value = None
        self._attr_available = True

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        return self._attr_native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(
                self._handle_coordinator_update,
                immediate=False,
            )
        )
        # Initial read
        await self.async_update()

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            if not self.coordinator.device.connected:
                self._attr_available = False
                return
            
            value = await self.coordinator.device.read_gatt(self._target_uuid)
            if value is not None:
                self._attr_native_value = value.hex() if isinstance(value, (bytes, bytearray)) else value
                self._attr_available = True
            else:
                self._attr_available = False
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.debug("Error reading characteristic %s: %s", self._target_uuid, err)
            self._attr_available = False

