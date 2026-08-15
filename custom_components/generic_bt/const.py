"""Constants"""
import voluptuous as vol
from enum import Enum

from homeassistant.helpers.config_validation import make_entity_service_schema
import homeassistant.helpers.config_validation as cv

DOMAIN = "generic_bt"
DEVICE_STARTUP_TIMEOUT_SECONDS = 30
CONF_CHARACTERISTIC_READERS = "characteristic_readers"
CONF_CHARACTERISTIC_NAME = "characteristic_name"
CONF_TARGET_UUID = "target_uuid"

class Schema(Enum):
    """General used service schema definition"""

    WRITE_GATT = make_entity_service_schema(
        {
            vol.Required("target_uuid"): cv.string,
            vol.Required("data"): cv.string
        }
    )
    READ_GATT = make_entity_service_schema(
        {
            vol.Required("target_uuid"): cv.string
        }
    )
