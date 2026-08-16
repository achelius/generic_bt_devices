from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_PIN, DEFAULT_PIN, DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class GateControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle automatic bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Confirm setup of a bluetooth-discovered device."""
        assert self._discovery_info is not None
        name = self._discovery_info.name or self._discovery_info.address
        if user_input is not None:
            return self.async_create_entry(
                title=name,
                data={
                    "address": self._discovery_info.address,
                    CONF_PIN: user_input[CONF_PIN],
                },
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_PIN, default=DEFAULT_PIN): str}
            ),
            description_placeholders={"name": name},
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle manual setup: scan for devices and let user pick one."""
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            all_discovered = {
                info.address: info
                for info in async_discovered_service_info(self.hass, connectable=True)
            }
            info = all_discovered.get(address)
            name = (info.name if info else None) or address
            return self.async_create_entry(
                title=name,
                data={"address": address, CONF_PIN: user_input[CONF_PIN]},
            )

        discovered = {
            info.address: info
            for info in async_discovered_service_info(self.hass, connectable=True)
            if SERVICE_UUID in [s.lower() for s in (info.service_uuids or [])]
        }

        if not discovered:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                errors={"base": "no_devices_found"},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("address"): vol.In(
                        {
                            addr: f"{info.name or addr} ({addr})"
                            for addr, info in discovered.items()
                        }
                    ),
                    vol.Required(CONF_PIN, default=DEFAULT_PIN): str,
                }
            ),
        )
