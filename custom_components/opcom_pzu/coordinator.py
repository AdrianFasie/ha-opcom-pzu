"""OPCOM PZU coordinator — fetches PT15 XML and injects HA statistics."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    OPCOM_XML_URL,
    POLLING_END_HOUR,
    POLLING_START_HOUR,
    ROMANIA_TZ,
    SCAN_INTERVAL_MINUTES,
    STATISTIC_ID,
)

_LOGGER = logging.getLogger(__name__)

# HA changed the recorder import path between 2023 and 2024 releases
try:
    from homeassistant.components.recorder.models.statistics import (
        StatisticData,
        StatisticMetaData,
    )
except ImportError:
    from homeassistant.components.recorder.models import (  # type: ignore[no-redef]
        StatisticData,
        StatisticMetaData,
    )
from homeassistant.components.recorder.statistics import async_import_statistics

_HOME_URL = "https://www.opcom.ro/acasa/ro"
_EXPORT_PAGE_URL = "https://www.opcom.ro/grafice-ip-raportPIP-si-volumTranzactionat/ro"

# Headers for the homepage warmup (no Referer, Sec-Fetch-Site: none)
_BROWSE_HEADERS: dict[str, str] = {
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
    "Cache-Control": "max-age=0",
}

# Headers for the actual XML export request
_DATA_HEADERS: dict[str, str] = {
    **_BROWSE_HEADERS,
    "Accept": "application/xml,text/xml,*/*;q=0.9",
    "Referer": _EXPORT_PAGE_URL,
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
}


class OpcomPZUCoordinator(DataUpdateCoordinator):
    """Fetch PZU prices from OPCOM, cache them, and push as HA statistics."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self._session = session
        self._today_date: date | None = None
        self._today_prices: list[float] = []
        self._tomorrow_date: date | None = None
        self._tomorrow_prices: list[float] = []
        self._tomorrow_loaded: bool = False

    # ------------------------------------------------------------------
    # DataUpdateCoordinator
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict:
        now_ro = datetime.now(ROMANIA_TZ)
        today = now_ro.date()
        tomorrow = today + timedelta(days=1)

        if self._today_date is None or self._today_date != today:
            # First run, or calendar day has rolled over
            await self._handle_new_day(today, tomorrow)
        elif (
            not self._tomorrow_loaded
            and POLLING_START_HOUR <= now_ro.hour < POLLING_END_HOUR
        ):
            # Inside the publication window — poll for tomorrow's prices
            prices = await self._fetch_prices(tomorrow)
            if prices:
                self._tomorrow_prices = prices
                self._tomorrow_date = tomorrow
                self._tomorrow_loaded = True
                _LOGGER.info("Tomorrow's PZU prices (%s) are now available", tomorrow)
                self._inject_statistics()

        return {
            "today_date": self._today_date,
            "today_prices": self._today_prices,
            "tomorrow_date": self._tomorrow_date if self._tomorrow_loaded else None,
            "tomorrow_prices": self._tomorrow_prices,
            "tomorrow_available": self._tomorrow_loaded,
        }

    # ------------------------------------------------------------------
    # Day-change handling
    # ------------------------------------------------------------------

    async def _handle_new_day(self, today: date, tomorrow: date) -> None:
        if self._tomorrow_loaded and self._tomorrow_date == today:
            # Reuse cached data — no extra HTTP request needed
            _LOGGER.debug("Rolling tomorrow (%s) into today", today)
            self._today_prices = self._tomorrow_prices
        else:
            prices = await self._fetch_prices(today)
            if not prices:
                # Don't raise UpdateFailed — let the sensor be unavailable and retry next tick
                _LOGGER.warning(
                    "Could not load PZU prices for %s; sensor will be unavailable until next retry",
                    today,
                )
                self._today_prices = []
            else:
                self._today_prices = prices

        self._today_date = today
        self._tomorrow_prices = []
        self._tomorrow_date = tomorrow
        self._tomorrow_loaded = False

        # Try to get tomorrow immediately (may already be published)
        prices = await self._fetch_prices(tomorrow)
        if prices:
            self._tomorrow_prices = prices
            self._tomorrow_loaded = True
            _LOGGER.info("Tomorrow's PZU prices (%s) loaded at startup", tomorrow)

        if self._today_prices:
            self._inject_statistics()

    # ------------------------------------------------------------------
    # HTTP fetch + XML parse
    # ------------------------------------------------------------------

    async def _warm_session(self) -> None:
        """Visit the OPCOM homepage to establish session cookies."""
        try:
            async with self._session.get(
                _HOME_URL,
                headers=_BROWSE_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                resp.raise_for_status()
                _LOGGER.debug("Session warmed up via OPCOM homepage")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Session warmup failed (will still try XML): %s", err)

    async def _fetch_prices(self, target_date: date) -> list[float]:
        """Return list of 96 prices for target_date, or [] if not published yet."""
        url = OPCOM_XML_URL.format(
            day=target_date.day,
            month=target_date.month,
            year=target_date.year,
        )
        try:
            text = await self._get_xml(url)
        except aiohttp.ClientResponseError as err:
            if err.status == 403:
                _LOGGER.debug("403 on XML; warming session and retrying")
                await self._warm_session()
                try:
                    text = await self._get_xml(url)
                except aiohttp.ClientError as retry_err:
                    _LOGGER.warning(
                        "Failed to fetch OPCOM prices for %s after warmup: %s",
                        target_date, retry_err,
                    )
                    return []
            else:
                _LOGGER.warning(
                    "Failed to fetch OPCOM prices for %s: HTTP %s",
                    target_date, err.status,
                )
                return []
        except aiohttp.ClientError as err:
            _LOGGER.warning("Failed to fetch OPCOM prices for %s: %s", target_date, err)
            return []

        return _parse_xml(text)

    async def _get_xml(self, url: str) -> str:
        """GET url and return the response text. Raises aiohttp errors on failure."""
        async with self._session.get(
            url,
            headers=_DATA_HEADERS,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            return await resp.text(errors="replace")

    # ------------------------------------------------------------------
    # Statistics injection
    # ------------------------------------------------------------------

    def _inject_statistics(self) -> None:
        """Push all loaded prices into the HA statistics database with proper timestamps."""
        metadata = StatisticMetaData(
            has_mean=True,
            has_sum=False,
            name="OPCOM PZU",
            source=DOMAIN,
            statistic_id=STATISTIC_ID,
            unit_of_measurement="RON/MWh",
        )

        stats: list[StatisticData] = []

        entries: list[tuple[date, list[float]]] = [(self._today_date, self._today_prices)]
        if self._tomorrow_loaded:
            entries.append((self._tomorrow_date, self._tomorrow_prices))

        for target_date, prices in entries:
            if not target_date or not prices:
                continue
            day_start = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                tzinfo=ROMANIA_TZ,
            )
            for i, price in enumerate(prices):
                stats.append(
                    StatisticData(
                        start=day_start + timedelta(minutes=15 * i),
                        mean=price,
                    )
                )

        async_import_statistics(self.hass, metadata, stats)
        _LOGGER.debug("Injected %d price statistics into recorder", len(stats))


# ---------------------------------------------------------------------------
# XML parser
# ---------------------------------------------------------------------------

def _parse_xml(text: str) -> list[float]:
    """Parse OPCOM PT15 XML and return prices ordered by interval (1 → 96).

    Returns an empty list if the XML contains no <Detail> elements
    (meaning prices are not published yet for that date).
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as err:
        _LOGGER.error("Failed to parse OPCOM XML: %s", err)
        return []

    intervals: dict[int, float] = {}
    for detail in root.findall("Detail"):
        try:
            interval = int(detail.findtext("Interval") or "")
            price = float(detail.findtext("Price") or "")
            intervals[interval] = price
        except (ValueError, TypeError):
            continue

    if not intervals:
        return []

    return [intervals[i] for i in sorted(intervals)]
