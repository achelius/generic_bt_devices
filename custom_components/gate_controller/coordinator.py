from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CHAR_BATTERY, CHAR_GATE_CONTROL, CHAR_REBOOT, CHAR_WIFI_CONTROL, DOMAIN

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(seconds=120)


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
            current = dict(self.data or {})
            # Battery is primarily updated via BLE notifications (start_notify).
            # Fall back to read_gatt_char only if no notification has arrived yet.
            if "battery" not in current:
                try:
                    raw = await self._client.read_gatt_char(CHAR_BATTERY)
                    if raw:
                        battery_val = raw[0]  # always single byte (0-100%); extra bytes are GATT metadata
                        if len(raw) != 1:
                            _LOGGER.warning(
                                "Battery characteristic returned %d bytes (expected 1); "
                                "using first byte only. Raw: %s (%d%%)",
                                len(raw), raw.hex(), battery_val,
                            )
                        else:
                            _LOGGER.debug("Battery read fallback: %d%%", battery_val)
                        current["battery"] = battery_val
                except BleakError as err:
                    _LOGGER.debug("Battery read fallback failed: %s", err)
            try:
                raw = await self._client.read_gatt_char(CHAR_WIFI_CONTROL)
                if raw:
                    wifi_val = bool(raw[0])
                    _LOGGER.debug("WiFi raw value: %s (0x%02x = %s)", raw.hex(), raw[0], "connected" if wifi_val else "disconnected")
                    current["wifi_connected"] = wifi_val
            except BleakError as err:
                _LOGGER.debug("Could not read WiFi status: %s", err)
            return current
        return self.data or {}

    async def _ensure_connected(self) -> None:
        async with self._lock:
            if self._client and self._client.is_connected:
                return
            try:
                # Get device from Bluetooth scanner if available
                device = async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if not device:
                    _LOGGER.debug(
                        "Device %s not in scanner cache, cannot establish connection",
                        self.address,
                    )
                    return
                # Use establish_connection from bleak_retry_connector for reliability
                # use_services_cache=False forces fresh GATT discovery, preventing stale
                # handle mappings after firmware updates
                client = await establish_connection(
                    BleakClient,
                    device,
                    name=self.address,
                    disconnected_callback=self._on_disconnect,
                    use_services_cache=False,                    
                )
                self._client = client
                # Subscribe to notifications; fall back to polling if CCCD write is rejected
                try:
                    await client.start_notify(CHAR_BATTERY, self._on_battery_notify)
                    _LOGGER.warning(
                        "Subscribed to battery notifications on %s — "
                        "waiting for ESPHome to push first notify()",
                        self.address,
                    )
                except BleakError as err:
                    _LOGGER.warning(
                        "Battery notifications unavailable on %s: %s",
                        self.address, err,
                    )
                try:
                    await client.start_notify(CHAR_WIFI_CONTROL, self._on_wifi_status_notify)
                    _LOGGER.warning("Subscribed to WiFi status notifications on %s", self.address)
                except BleakError as err:
                    _LOGGER.debug(
                        "WiFi status notifications unavailable on %s (polling instead): %s",
                        self.address, err,
                    )
                _LOGGER.warning("Connected to %s", self.address)
            except BleakError as err:
                _LOGGER.warning("Failed to connect to %s: %s", self.address, err)

    @callback
    def _on_disconnect(self, _client: BleakClient) -> None:
        self._client = None
        _LOGGER.debug("Disconnected from %s", self.address)

    @callback
    def _on_battery_notify(self, _sender, data: bytearray) -> None:
        if data:
            if len(data) != 1:
                _LOGGER.warning(
                    "Battery characteristic returned %d bytes (expected 1). "
                    "Raw: %s — ESPHome BLE server may not support GATT reads correctly; "
                    "ensure the characteristic value uses a lambda and calls notify().",
                    len(data), data.hex(),
                )
            battery_val = data[0]
            _LOGGER.warning("Battery notify: %d%%", battery_val)
            self.async_set_updated_data({**(self.data or {}), "battery": battery_val})

    @callback
    def _on_wifi_status_notify(self, _sender, data: bytearray) -> None:
        if data:
            connected = bool(data[0])
            _LOGGER.debug("WiFi status notify: %s", "connected" if connected else "disconnected")
            self.async_set_updated_data({**(self.data or {}), "wifi_connected": connected})

    async def _write_characteristic(self, char_uuid: str, data: bytes) -> None:
        await self._ensure_connected()
        if not (self._client and self._client.is_connected):
            raise HomeAssistantError(
                f"Cannot reach Gate Controller at {self.address}: device not found"
            )
        try:
            await self._client.write_gatt_char(char_uuid, data, response=False)
        except BleakError as err:
            # Retry once after reconnecting
            _LOGGER.debug("Write to %s failed, attempting reconnect and retry: %s", self.address, err)
            async with self._lock:
                self._client = None
            await self._ensure_connected()
            if not (self._client and self._client.is_connected):
                raise HomeAssistantError(
                    f"Cannot reach Gate Controller at {self.address}: failed to reconnect"
                ) from err
            try:
                await self._client.write_gatt_char(char_uuid, data, response=False)
            except BleakError as retry_err:
                raise HomeAssistantError(f"BLE write failed after retry: {retry_err}") from retry_err

    async def async_open_gate(self) -> None:
        await self._write_characteristic(CHAR_GATE_CONTROL, self.pin.encode())

    async def async_enable_wifi(self) -> None:
        await self._write_characteristic(CHAR_WIFI_CONTROL, b"\x01")

    async def async_disable_wifi(self) -> None:
        await self._write_characteristic(CHAR_WIFI_CONTROL, b"\x00")

    async def async_reboot(self) -> None:
        await self._write_characteristic(CHAR_REBOOT, b"\x01")

    async def async_disconnect(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._client = None
