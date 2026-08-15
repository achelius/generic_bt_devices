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
        # Poll if there are characteristics configured
        # Connection will be established during the read
        characteristics = self._get_characteristics()
        return bool(characteristics)

    def _get_characteristics(self) -> list[dict]:
        """Get the list of characteristics to read from config entry."""
        if not self.config_entry:
            return []
        return self.config_entry.options.get(CONF_CHARACTERISTIC_READERS, [])

    async def _async_update(self, service_info: bluetooth.BluetoothServiceInfoBleak | None = None) -> None:
        """Poll the device and read all characteristic values."""
        _LOGGER.debug(f"Polling device {self.device_name}")
        
        # Read all configured characteristics
        characteristics = self._get_characteristics()
        if not characteristics:
            _LOGGER.debug("No characteristics configured to poll")
            return
        
        _LOGGER.debug(f"Found {len(characteristics)} characteristics to read")
        successful_reads = 0
        failed_reads = 0
        
        for i, characteristic in enumerate(characteristics):
            target_uuid = characteristic.get(CONF_TARGET_UUID)
            char_name = characteristic.get(CONF_CHARACTERISTIC_NAME)
            if not target_uuid:
                _LOGGER.warning(f"Characteristic {i} has no UUID")
                continue
            
            _LOGGER.debug(f"Reading characteristic {i}: {char_name} ({target_uuid})")
            try:
                value = await self.device.read_gatt(target_uuid)
                if value is not None:
                    # Store as hex string if bytes, otherwise as-is
                    hex_value = value.hex() if isinstance(value, (bytes, bytearray)) else str(value)
                    self._characteristic_values[target_uuid] = hex_value
                    _LOGGER.info(f"✓ Successfully read {char_name} ({target_uuid}): {hex_value}")
                    successful_reads += 1
                else:
                    self._characteristic_values[target_uuid] = None
                    _LOGGER.warning(f"✗ Read returned None for {char_name} ({target_uuid})")
                    failed_reads += 1
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error(f"✗ Error reading characteristic {char_name} ({target_uuid}): {err}", exc_info=True)
                self._characteristic_values[target_uuid] = None
                failed_reads += 1
        
        _LOGGER.info(f"Polling complete for {self.device_name}: {successful_reads} successful, {failed_reads} failed")

    def get_characteristic_value(self, target_uuid: str) -> str | None:
        """Get the last read value for a characteristic."""
        value = self._characteristic_values.get(target_uuid)
        _LOGGER.debug(f"get_characteristic_value({target_uuid}): {value}")
        return value

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
                # Trigger initial poll after device is ready
                _LOGGER.debug(f"Device {self.device_name} is ready, triggering initial poll")
                try:
                    await self._async_update(None)
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.debug(f"Error during initial poll: {err}")
                return True
        return False
