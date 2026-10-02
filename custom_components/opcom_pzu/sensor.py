"""OPCOM PZU sensor — single entity showing the current interval price."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ROMANIA_TZ, STATISTIC_ID
from .coordinator import OpcomPZUCoordinator

_SOURCE_URL = "https://www.opcom.ro/grafice-ip-raportPIP-si-volumTranzactionat/ro"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: OpcomPZUCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([OpcomPZUSensor(coordinator)])


class OpcomPZUSensor(CoordinatorEntity, SensorEntity):
    """Romania day-ahead electricity price for the current 15-min interval."""

    _attr_has_entity_name = True
    _attr_name = "PZU"
    _attr_unique_id = "opcom_pzu_price"
    _attr_icon = "mdi:lightning-bolt"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "RON/MWh"

    def __init__(self, coordinator: OpcomPZUCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "opcom_pzu")},
            name="OPCOM PZU",
            manufacturer="OPCOM",
            model="Day-Ahead Electricity Market",
            configuration_url=_SOURCE_URL,
            entry_type=DeviceEntryType.SERVICE,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _current_index() -> int:
        """0-based index of the current 15-min interval (0 = 00:00–00:15)."""
        now = datetime.now(ROMANIA_TZ)
        return (now.hour * 60 + now.minute) // 15

    # ------------------------------------------------------------------
    # SensorEntity
    # ------------------------------------------------------------------

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        prices: list[float] = self.coordinator.data.get("today_prices", [])
        idx = self._current_index()
        if prices and 0 <= idx < len(prices):
            return round(prices[idx], 2)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        data = self.coordinator.data
        today_prices: list[float] = data.get("today_prices", [])
        idx = self._current_index()

        attrs: dict = {
            "current_interval": _interval_label(idx),
            "price_date": str(data["today_date"]) if data.get("today_date") else None,
            "tomorrow_available": data.get("tomorrow_available", False),
            # statistic_id helps users know which ID to use in statistics-graph card
            "statistic_id": STATISTIC_ID,
            "today_prices": _prices_to_timed_dict(today_prices),
        }

        if data.get("tomorrow_available"):
            attrs["tomorrow_date"] = str(data["tomorrow_date"])
            attrs["tomorrow_prices"] = _prices_to_timed_dict(
                data.get("tomorrow_prices", [])
            )

        return attrs


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _interval_label(idx: int) -> str:
    """Return a human-readable label like '14:00–14:15' for interval index idx."""
    h_s, m_s = divmod(idx * 15, 60)
    h_e, m_e = divmod((idx + 1) * 15, 60)
    return f"{h_s:02d}:{m_s:02d}–{h_e:02d}:{m_e:02d}"


def _prices_to_timed_dict(prices: list[float]) -> dict[str, float]:
    """Convert ordered price list to {'00:00': 977.08, '00:15': 983.58, ...}."""
    result: dict[str, float] = {}
    for i, price in enumerate(prices):
        h, m = divmod(i * 15, 60)
        result[f"{h:02d}:{m:02d}"] = price
    return result
