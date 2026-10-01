"""Config flow for OPCOM PZU."""
from __future__ import annotations

import aiohttp

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, OPCOM_URL
from .coordinator import BROWSE_HEADERS, DATA_HEADERS

_HOME_URL = "https://www.opcom.ro/acasa/ro"


class OpcomPZUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the setup flow for OPCOM PZU."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        """Show the confirmation form and verify connectivity on submit."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            try:
                # Warm up session with homepage first, then check data page
                async with session.get(
                    _HOME_URL,
                    headers=BROWSE_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    resp.raise_for_status()

                async with session.get(
                    OPCOM_URL,
                    headers=DATA_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    resp.raise_for_status()
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="OPCOM PZU", data={})

        return self.async_show_form(step_id="user", errors=errors)
