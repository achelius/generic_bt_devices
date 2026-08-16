from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from bleak import BleakClient, BleakError
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CHAR_BATTERY, CHAR_GATE_CONTROL, CHAR_WIFI_CONTROL, DOMAIN

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(seconds=600)


class GateControllerCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, address: str, pin: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self.address = address
        self.pin = pin
        self._client: BleakClient | None = None
        self._lock = asyncio.Lock()

    async def _async_update_data(self) -> dict:
        await self._ensure_connected()
        if self._client and self._client.is_connected:
            try:
                raw = await self._client.read_gatt_char(CHAR_BATTERY)
                if raw:
                    return {"battery": raw[0]}
            except BleakError as err:
                _LOGGER.debug("Could not read battery: %s", err)
        return self.data or {}

    async def _ensure_connected(self) -> None:
        async with self._lock:
            if self._client and self._client.is_connected:
                return
            device = async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if not device:
                _LOGGER.debug("Device %s not found in BLE scanner cache", self.address)
                return
            try:
                client = BleakClient(device, disconnected_callback=self._on_disconnect)
                await client.connect()
                await client.start_notify(CHAR_BATTERY, self._on_battery_notify)
                self._client = client
                _LOGGER.debug("Connected to %s and subscribed to battery notifications", self.address)
            except BleakError as err:
                _LOGGER.warning("Failed to connect to %s: %s", self.address, err)

    @callback
    def _on_disconnect(self, _client: BleakClient) -> None:
        self._client = None
        _LOGGER.debug("Disconnected from %s", self.address)

    @callback
    def _on_battery_notify(self, _sender, data: bytearray) -> None:
        if data:
            _LOGGER.debug("Battery notify: %d%%", data[0])
            self.async_set_updated_data({**(self.data or {}), "battery": data[0]})

    async def _write_characteristic(self, char_uuid: str, data: bytes) -> None:
        await self._ensure_connected()
        if not (self._client and self._client.is_connected):
            raise HomeAssistantError(
                f"Cannot reach Gate Controller at {self.address}: device not found"
            )
        try:
            await self._client.write_gatt_char(char_uuid, data, response=False)
        except BleakError as err:
            raise HomeAssistantError(f"BLE write failed: {err}") from err

    async def async_open_gate(self) -> None:
        await self._write_characteristic(CHAR_GATE_CONTROL, self.pin.encode())

    async def async_enable_wifi(self) -> None:
        await self._write_characteristic(CHAR_WIFI_CONTROL, b"\x01")

    async def async_disable_wifi(self) -> None:
        await self._write_characteristic(CHAR_WIFI_CONTROL, b"\x00")

    async def async_disconnect(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._client = None
