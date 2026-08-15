"""generic bt device"""

from uuid import UUID
import asyncio
import logging

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

_LOGGER = logging.getLogger(__name__)


class GenericBTDevice:
    """Generic BT Device Class"""
    def __init__(self, ble_device):
        self._ble_device = ble_device
        self._client: BleakClient | None = None
        self._lock = asyncio.Lock()

    async def update(self):
        """Update device state."""
        pass

    async def stop(self):
        """Stop the device connection."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.debug(f"Error disconnecting: {err}")
            finally:
                self._client = None

    @property
    def connected(self):
        """Check if device is connected."""
        return self._client is not None

    async def get_client(self):
        """Get or create a BleakClient connection using retry connector."""
        async with self._lock:
            if not self._client:
                _LOGGER.debug("Connecting to device with retry connector")
                try:
                    self._client = await establish_connection(
                        BleakClient,
                        device=self._ble_device,
                        name=self._ble_device.name,
                        timeout=30
                    )
                    _LOGGER.debug("Successfully connected to device")
                except asyncio.TimeoutError as exc:
                    _LOGGER.debug("Timeout connecting to device", exc_info=True)
                    raise exc
                except BleakError as exc:
                    _LOGGER.debug("Error connecting to device", exc_info=True)
                    raise exc
            else:
                _LOGGER.debug("Connection reused")
            return self._client

    def _parse_uuid(self, target_uuid: str) -> UUID:
        """Parse UUID string (handles both full and short UUIDs)."""
        # Remove curly braces if present
        uuid_str = target_uuid.strip("{}")
        
        # If it's a short UUID (4 hex chars), expand it to full format
        if len(uuid_str) == 4:
            uuid_str = f"0000{uuid_str}-0000-1000-8000-00805f9b34fb"
        
        return UUID(uuid_str)

    async def write_gatt(self, target_uuid, data):
        """Write data to a GATT characteristic."""
        client = await self.get_client()
        uuid = self._parse_uuid(target_uuid)
        data_as_bytes = bytearray.fromhex(data)
        await client.write_gatt_char(uuid, data_as_bytes, True)
        _LOGGER.debug(f"Wrote to {target_uuid}: {data}")

    async def read_gatt(self, target_uuid):
        """Read data from a GATT characteristic."""
        _LOGGER.debug(f"read_gatt called with uuid: {target_uuid}")
        client = await self.get_client()
        uuid = self._parse_uuid(target_uuid)
        _LOGGER.debug(f"Parsed UUID: {uuid}")
        try:
            data = await client.read_gatt_char(uuid)
            hex_value = data.hex() if data else None
            _LOGGER.debug(f"Successfully read from {target_uuid}: raw={data}, hex={hex_value}, type={type(data)}")
            return data
        except Exception as err:
            _LOGGER.error(f"Failed to read characteristic {target_uuid}: {err}", exc_info=True)
            raise

    def update_from_advertisement(self, advertisement):
        """Update device info from BLE advertisement."""
        pass
