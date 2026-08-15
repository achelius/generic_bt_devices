"""Config flow for GenericBT integration."""
from __future__ import annotations

import logging
from typing import Any

from bluetooth_data_tools import human_readable_name
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_CHARACTERISTIC_READERS, CONF_CHARACTERISTIC_NAME, CONF_TARGET_UUID
from .generic_bt_api.device import GenericBTDevice

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Generic BT."""

    VERSION = 1
    
    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlow:
        """Return options flow."""
        return OptionsFlow(config_entry)

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._selected_address: str | None = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> FlowResult:
        """Handle the bluetooth discovery step."""
        #if discovery_info.name.startswith(UNSUPPORTED_SUB_MODEL):
        #    return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": human_readable_name(None, discovery_info.name, discovery_info.address)}
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the user step to pick discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            discovery_info = self._discovered_devices[address]
            local_name = discovery_info.name
            await self.async_set_unique_id(discovery_info.address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            device = GenericBTDevice(discovery_info.device)
            try:
                await device.update()
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Unexpected error")
            else:
                await device.stop()
                self._selected_address = address
                return await self.async_step_add_characteristic()

        if discovery := self._discovery_info:
            self._discovered_devices[discovery.address] = discovery
        else:
            current_addresses = self._async_current_ids()
            for discovery in async_discovered_service_info(self.hass):
                if (
                    discovery.address in current_addresses
                    or discovery.address in self._discovered_devices
                ):
                    continue
                self._discovered_devices[discovery.address] = discovery

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        service_info.address: (f"{service_info.name} ({service_info.address})")
                        for service_info in self._discovered_devices.values()
                    }
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_add_characteristic(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle adding a characteristic reader to the device."""
        if user_input is not None:
            discovery_info = self._discovered_devices[self._selected_address]
            local_name = discovery_info.name
            
            characteristics: list[dict[str, str]] = [{
                CONF_CHARACTERISTIC_NAME: user_input[CONF_CHARACTERISTIC_NAME],
                CONF_TARGET_UUID: user_input[CONF_TARGET_UUID]
            }]
            
            return self.async_create_entry(
                title=local_name,
                data={CONF_ADDRESS: self._selected_address},
                options={CONF_CHARACTERISTIC_READERS: characteristics}
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CHARACTERISTIC_NAME): cv.string,
                vol.Required(CONF_TARGET_UUID): cv.string,
            }
        )
        
        return self.async_show_form(
            step_id="add_characteristic",
            data_schema=data_schema,
            description_placeholders={"device": self._discovered_devices[self._selected_address].name}
        )


class OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Generic BT integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial options step."""
        if user_input is not None:
            characteristics: list[dict[str, str]] = []
            
            # Add new characteristic if provided
            if user_input.get(CONF_CHARACTERISTIC_NAME) and user_input.get(CONF_TARGET_UUID):
                characteristics.append({
                    CONF_CHARACTERISTIC_NAME: user_input[CONF_CHARACTERISTIC_NAME],
                    CONF_TARGET_UUID: user_input[CONF_TARGET_UUID]
                })
            
            # Keep existing characteristics
            existing = self.config_entry.options.get(CONF_CHARACTERISTIC_READERS, [])
            characteristics.extend(existing)
            
            return self.async_create_entry(
                title="",
                data={CONF_CHARACTERISTIC_READERS: characteristics}
            )

        current_characteristics = self.config_entry.options.get(CONF_CHARACTERISTIC_READERS, [])
        char_list = "\n".join(
            f"- {char.get(CONF_CHARACTERISTIC_NAME)}: {char.get(CONF_TARGET_UUID)}"
            for char in current_characteristics
        ) if current_characteristics else "No characteristics configured"

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_CHARACTERISTIC_NAME): cv.string,
                vol.Optional(CONF_TARGET_UUID): cv.string,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={"characteristics": char_list}
        )