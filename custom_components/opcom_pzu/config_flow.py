"""Config flow for OPCOM PZU."""
from __future__ import annotations

import aiohttp

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_HOME_URL = "https://www.opcom.ro/acasa/ro"
_EXPORT_PAGE_URL = "https://www.opcom.ro/grafice-ip-raportPIP-si-volumTranzactionat/ro"

_BROWSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

_DATA_HEADERS = {
    **_BROWSE_HEADERS,
    "Accept": "application/xml,text/xml,*/*;q=0.9",
    "Referer": _EXPORT_PAGE_URL,
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
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

            session = async_get_clientsession(self.hass)
            try:
                # Any HTTP response (even 403) means the server is reachable.
                # The coordinator handles auth/warmup at runtime — here we only
                # need to confirm basic network connectivity to opcom.ro.
                async with session.get(
                    _HOME_URL,
                    headers=_BROWSE_HEADERS,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True,
                ):
                    pass
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="OPCOM PZU", data={})

        return self.async_show_form(step_id="user", errors=errors)
