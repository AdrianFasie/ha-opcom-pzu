"""Constants for the OPCOM PZU integration."""

DOMAIN = "opcom_pzu"
OPCOM_URL = "https://www.opcom.ro/grafice-ip-raportPIP-si-volumTranzactionat/ro"
SCAN_INTERVAL_MINUTES = 30

# (sensor name, minutes per interval, intervals per day)
INTERVAL_CONFIGS: list[tuple[str, int, int]] = [
    ("PT15", 15, 96),
    ("PT30", 30, 48),
    ("PT60", 60, 24),
]
