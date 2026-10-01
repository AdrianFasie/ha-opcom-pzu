"""OPCOM PZU sensor entities."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INTERVAL_CONFIGS, OPCOM_URL
from .coordinator import OpcomPZUCoordinator

_ROMANIA_TZ = ZoneInfo("Europe/Bucharest")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OPCOM PZU sensors from a config entry."""
    coordinator: OpcomPZUCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        OpcomPZUSensor(coordinator, name, minutes, periods)
        for name, minutes, periods in INTERVAL_CONFIGS
    )


class OpcomPZUSensor(CoordinatorEntity, SensorEntity):
    """Price sensor for one OPCOM PZU time-interval resolution."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:lightning-bolt"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "RON/MWh"

    def __init__(
        self,
        coordinator: OpcomPZUCoordinator,
        interval_name: str,
        minutes: int,
        periods: int,
    ) -> None:
        super().__init__(coordinator)
        self._interval_name = interval_name
        self._minutes = minutes
        self._periods = periods
        self._attr_name = interval_name          # shown as "OPCOM PZU PT15" etc.
        self._attr_unique_id = f"opcom_pzu_{interval_name.lower()}"

    # ------------------------------------------------------------------
    # Device — groups all three sensors under one logical device
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "opcom_pzu")},
            name="OPCOM PZU",
            manufacturer="OPCOM",
            model="Day-Ahead Electricity Market",
            configuration_url=OPCOM_URL,
            entry_type=DeviceEntryType.SERVICE,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_index(self) -> int:
        """0-based interval index for the current Romania local time."""
        now = datetime.now(_ROMANIA_TZ)
        return (now.hour * 60 + now.minute) // self._minutes

    # ------------------------------------------------------------------
    # SensorEntity
    # ------------------------------------------------------------------

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        prices = self.coordinator.data.get(self._interval_name, [])
        idx = self._current_index()
        if prices and 0 <= idx < len(prices):
            return round(prices[idx], 2)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        prices = self.coordinator.data.get(self._interval_name, [])
        idx = self._current_index()
        attrs: dict = {
            "interval": self._interval_name,
            "interval_minutes": self._minutes,
            "current_interval_index": idx,
            "source": OPCOM_URL,
        }
        if prices:
            attrs["all_prices"] = prices
            attrs["min_price_ron_mwh"] = round(min(prices), 2)
            attrs["max_price_ron_mwh"] = round(max(prices), 2)
            attrs["avg_price_ron_mwh"] = round(sum(prices) / len(prices), 2)
        return attrs
