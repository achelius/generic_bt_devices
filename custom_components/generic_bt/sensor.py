"""Support for Generic BT sensor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    
    # Always call async_add_entities, even if empty, to signal platform setup is complete
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
        # Include name in unique_id to prevent collisions when same UUID used multiple times
        self._attr_unique_id = f"{coordinator.base_unique_id}_{name}_{target_uuid}".lower().replace(" ", "_")
        _LOGGER.debug(f"Initializing sensor: name={name}, uuid={target_uuid}, unique_id={self._attr_unique_id}")

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        value = self.coordinator.get_characteristic_value(self._target_uuid)
        _LOGGER.debug(f"Getting native_value for {self._attr_name} ({self._target_uuid}): {value}")
        return value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available if coordinator is ready (device is connected)
        # Value will be None initially but entity should still be available
        available = self.coordinator.last_update_success
        _LOGGER.debug(f"Checking availability for {self._attr_name}: {available} (last_update_success={self.coordinator.last_update_success})")
        return available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        current_value = self.coordinator.get_characteristic_value(self._target_uuid)
        _LOGGER.debug(f"Coordinator update for {self._attr_name}: value={current_value}")
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"Sensor {self._attr_name} ({self._target_uuid}) added to hass, unique_id={self._attr_unique_id}")
        self.async_on_remove(
            self.coordinator.async_add_listener(
                self._handle_coordinator_update,
                immediate=True,
            )
        )
        _LOGGER.debug(f"Initial value for {self._attr_name}: {self.native_value}")

