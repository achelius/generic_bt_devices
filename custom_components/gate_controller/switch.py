from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GateControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GateControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WiFiSwitch(coordinator, entry)])


class WiFiSwitch(CoordinatorEntity[GateControllerCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "WiFi"
    _attr_icon = "mdi:wifi"

    def __init__(
        self,
        coordinator: GateControllerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def unique_id(self) -> str:
        return f"{self._entry.data['address']}_wifi"

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data:
            return self.coordinator.data.get("wifi_connected")
        return None

    @property
    def icon(self) -> str:
        if self.is_on:
            return "mdi:wifi"
        return "mdi:wifi-off"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["address"])},
            name=self._entry.title,
            manufacturer="RGC",
            model="RF Gate Controller",
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_enable_wifi()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_disable_wifi()
