"""Config flow for OPCOM PZU."""
from __future__ import annotations

from datetime import datetime

import aiohttp

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, OPCOM_XML_URL, ROMANIA_TZ

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,*/*;q=0.9",
}


class OpcomPZUConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the setup flow for OPCOM PZU."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            today = datetime.now(ROMANIA_TZ).date()
            url = OPCOM_XML_URL.format(
                day=today.day, month=today.month, year=today.year
            )
            try:
                session = async_get_clientsession(self.hass)
                async with session.get(
                    url,
                    headers=_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    resp.raise_for_status()
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="OPCOM PZU", data={})

        return self.async_show_form(step_id="user", errors=errors)
