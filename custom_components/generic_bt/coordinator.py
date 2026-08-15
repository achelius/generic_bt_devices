"""Provides the DataUpdateCoordinator."""
from __future__ import annotations

import asyncio
import contextlib
import logging

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import ActiveBluetoothDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, callback
from bleak.backends.device import BLEDevice

from .generic_bt_api.device import GenericBTDevice
from .const import DOMAIN, DEVICE_STARTUP_TIMEOUT_SECONDS, CONF_CHARACTERISTIC_READERS, CONF_TARGET_UUID, CONF_CHARACTERISTIC_NAME

_LOGGER = logging.getLogger(__name__)

class GenericBTCoordinator(ActiveBluetoothDataUpdateCoordinator[None]):
    """Class to manage fetching generic bt data."""

    def __init__(self, hass: HomeAssistant, logger: logging.Logger, ble_device: BLEDevice, device: GenericBTDevice, device_name: str, base_unique_id: str, connectable: bool, config_entry: ConfigEntry | None = None) -> None:
        """Initialize global generic bt data updater."""
        super().__init__(hass=hass, logger=logger, address=ble_device.address, needs_poll_method=self._needs_poll, poll_method=self._async_update, mode=bluetooth.BluetoothScanningMode.ACTIVE, connectable=connectable)
        self.ble_device = ble_device
        self.device = device
        self.device_name = device_name
        self.base_unique_id = base_unique_id
        self.config_entry = config_entry
        self._ready_event = asyncio.Event()
        self._was_unavailable = True
        self._characteristic_values: dict[str, str | None] = {}

    @callback
    def _needs_poll(self, service_info: bluetooth.BluetoothServiceInfoBleak, seconds_since_last_poll: float | None) -> bool:
        """Return whether polling is needed."""
        # Poll if device is connected and has characteristics to read
        characteristics = self._get_characteristics()
        return bool(characteristics) and self.device.connected

    def _get_characteristics(self) -> list[dict]:
        """Get the list of characteristics to read from config entry."""
        if not self.config_entry:
            return []
        return self.config_entry.options.get(CONF_CHARACTERISTIC_READERS, [])

    async def _async_update(self, service_info: bluetooth.BluetoothServiceInfoBleak) -> None:
        """Poll the device and read all characteristic values."""
        await self.device.update()
        
        # Read all configured characteristics
        characteristics = self._get_characteristics()
        for characteristic in characteristics:
            target_uuid = characteristic.get(CONF_TARGET_UUID)
            char_name = characteristic.get(CONF_CHARACTERISTIC_NAME)
            if target_uuid:
                try:
                    value = await self.device.read_gatt(target_uuid)
                    if value is not None:
                        # Store as hex string if bytes, otherwise as-is
                        self._characteristic_values[target_uuid] = value.hex() if isinstance(value, (bytes, bytearray)) else value
                        _LOGGER.debug(f"Read {char_name} ({target_uuid}): {self._characteristic_values[target_uuid]}")
                    else:
                        self._characteristic_values[target_uuid] = None
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.debug(f"Error reading characteristic {char_name} ({target_uuid}): {err}")
                    self._characteristic_values[target_uuid] = None

    def get_characteristic_value(self, target_uuid: str) -> str | None:
        """Get the last read value for a characteristic."""
        return self._characteristic_values.get(target_uuid)

    @callback
    def _async_handle_unavailable(self, service_info: bluetooth.BluetoothServiceInfoBleak) -> None:
        """Handle the device going unavailable."""
        super()._async_handle_unavailable(service_info)
        self._was_unavailable = True

    @callback
    def _async_handle_bluetooth_event(self, service_info: bluetooth.BluetoothServiceInfoBleak, change: bluetooth.BluetoothChange) -> None:
        """Handle a Bluetooth event."""
        self.ble_device = service_info.device
        _LOGGER.debug(f"{DOMAIN} - _async_handle_bluetooth_event - {service_info} - {self.ble_device}")
        self._ready_event.set()

        if not self._was_unavailable:
            return

        self._was_unavailable = False
        self.device.update_from_advertisement(service_info.advertisement)
        super()._async_handle_bluetooth_event(service_info, change)

    async def async_wait_ready(self) -> bool:
        """Wait for the device to be ready."""
        with contextlib.suppress(asyncio.TimeoutError):
            async with asyncio.timeout(DEVICE_STARTUP_TIMEOUT_SECONDS):
                await self._ready_event.wait()
                return True
        return False
