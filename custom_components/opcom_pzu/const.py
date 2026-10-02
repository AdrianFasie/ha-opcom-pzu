"""Constants for the OPCOM PZU integration."""
from zoneinfo import ZoneInfo

DOMAIN = "opcom_pzu"

# DD and MM are zero-padded; use .format(day=, month=, year=)
OPCOM_XML_URL = (
    "https://www.opcom.ro/rapoarte-pzu-raportPIP-export-xml"
    "/{day:02d}/{month:02d}/{year}/ro?resolution=15"
)

SCAN_INTERVAL_MINUTES = 15

# Romania-time window during which OPCOM publishes next-day prices.
# Extended to 18:00 as a safety net in case of delayed publication.
POLLING_START_HOUR = 12
POLLING_END_HOUR = 18

# External statistics ID used in the statistics-graph Lovelace card
STATISTIC_ID = f"{DOMAIN}:pzu_price"

ROMANIA_TZ = ZoneInfo("Europe/Bucharest")
