from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GateControllerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GateControllerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        GateOpenButton(coordinator, entry),
        RebootButton(coordinator, entry),
    ])


class _GateControllerButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: GateControllerCoordinator, entry: ConfigEntry
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.data["address"])},
            name=self._entry.title,
            manufacturer="RGC",
            model="RF Gate Controller",
        )


class GateOpenButton(_GateControllerButton):
    _attr_name = "Open Gate"
    _attr_icon = "mdi:gate-open"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.data['address']}_open_gate"

    async def async_press(self) -> None:
        await self._coordinator.async_open_gate()


class RebootButton(_GateControllerButton):
    _attr_name = "Reboot"
    _attr_icon = "mdi:restart"

    @property
    def unique_id(self) -> str:
        return f"{self._entry.data['address']}_reboot"

    async def async_press(self) -> None:
        await self._coordinator.async_reboot()
