"""Config flow for OPCOM PZU."""
from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class OpcomPZUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the setup flow for OPCOM PZU."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="OPCOM PZU", data={})

        return self.async_show_form(step_id="user")
