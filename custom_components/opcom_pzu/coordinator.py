"""OPCOM PZU data coordinator — fetches and parses opcom.ro prices."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, INTERVAL_CONFIGS, OPCOM_URL, SCAN_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)

_HOME_URL = "https://www.opcom.ro/acasa/ro"

# Headers for the initial homepage visit (no Referer, Sec-Fetch-Site: none)
BROWSE_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

# Headers for the data page — adds Referer and changes Sec-Fetch-Site
DATA_HEADERS: dict[str, str] = {
    **BROWSE_HEADERS,
    "Referer": _HOME_URL,
    "Sec-Fetch-Site": "same-origin",
}


class OpcomPZUCoordinator(DataUpdateCoordinator):
    """Fetch and cache OPCOM PZU prices on a shared schedule."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self._session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _warm_session(self) -> None:
        """Visit the OPCOM homepage to pick up session cookies."""
        try:
            async with self._session.get(
                _HOME_URL,
                headers=BROWSE_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                resp.raise_for_status()
                _LOGGER.debug("Session warmed up via OPCOM homepage")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Session warmup failed (will still try data page): %s", err)

    async def _fetch_page(self) -> str:
        """Fetch the PZU data page and return its HTML."""
        async with self._session.get(
            OPCOM_URL,
            headers=DATA_HEADERS,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            return await resp.text(errors="replace")

    # ------------------------------------------------------------------
    # DataUpdateCoordinator
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, list[float]]:
        try:
            html = await self._fetch_page()
        except aiohttp.ClientResponseError as err:
            if err.status == 403:
                # Server rejected the request — warm up session and retry once
                _LOGGER.debug("403 on data page; warming session and retrying")
                await self._warm_session()
                try:
                    html = await self._fetch_page()
                except aiohttp.ClientError as retry_err:
                    raise UpdateFailed(
                        f"Error fetching OPCOM page after session warmup: {retry_err}"
                    ) from retry_err
            else:
                raise UpdateFailed(f"HTTP {err.status} from OPCOM") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching OPCOM page: {err}") from err

        data = _parse_html(html)
        if not any(data.values()):
            raise UpdateFailed(
                "No prices were parsed from the OPCOM page — "
                "the page structure may have changed"
            )
        return data


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------

def _parse_price(text: str) -> float | None:
    """Parse a Romanian/European-formatted number string to float."""
    text = text.strip()
    if not text or text in ("-", "N/A"):
        return None

    # Handle mixed separators: 1.234,56 (EU) vs 1,234.56 (EN)
    if "," in text and "." in text:
        if text.rindex(",") > text.rindex("."):
            text = text.replace(".", "").replace(",", ".")  # EU: 1.234,56
        else:
            text = text.replace(",", "")                    # EN: 1,234.56
    elif "," in text:
        after_comma = text.split(",")[-1]
        if len(after_comma) == 3:
            text = text.replace(",", "")   # thousands separator
        else:
            text = text.replace(",", ".")  # decimal separator

    try:
        value = float(text)
        return value if 0 < value < 100_000 else None
    except ValueError:
        return None


def _parse_html(html: str) -> dict[str, list[float]]:
    """Return a mapping of interval name → list of prices for the day."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    _LOGGER.debug("OPCOM page: found %d <table> elements", len(tables))

    result: dict[str, list[float]] = {}

    for interval_name, _minutes, expected_periods in INTERVAL_CONFIGS:
        # Pick the table whose data-row count is closest to the expected count
        best_table = None
        best_diff: int | None = None
        for table in tables:
            n_data_rows = sum(1 for r in table.find_all("tr") if r.find("td"))
            diff = abs(n_data_rows - expected_periods)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_table = table

        if best_table is None:
            _LOGGER.warning("No table found for interval %s", interval_name)
            result[interval_name] = []
            continue

        prices: list[float] = []
        for row in best_table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            for col in (2, 3, 1):
                if col < len(cells):
                    price = _parse_price(cells[col].get_text())
                    if price is not None:
                        prices.append(price)
                        break

        _LOGGER.debug(
            "Interval %s: parsed %d prices (expected %d)",
            interval_name,
            len(prices),
            expected_periods,
        )
        result[interval_name] = prices

    return result
