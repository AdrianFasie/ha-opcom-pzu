# OPCOM PZU — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/AdrianFasie/ha-opcom-pzu.svg)](https://github.com/AdrianFasie/ha-opcom-pzu/releases)
[![License](https://img.shields.io/github/license/AdrianFasie/ha-opcom-pzu.svg)](LICENSE)

Track Romania's **day-ahead electricity market (PZU)** prices directly in Home Assistant.  
Data is fetched from [opcom.ro](https://www.opcom.ro/grafice-ip-raportPIP-si-volumTranzactionat/ro) and updated every 30 minutes.

---

## Sensors

Three sensors are created automatically, each showing the price for the **current time interval**:

| Entity | Resolution | Description |
|---|---|---|
| `sensor.opcom_pzu_pt15` | 15 min | Current 15-minute interval price |
| `sensor.opcom_pzu_pt30` | 30 min | Current 30-minute interval price |
| `sensor.opcom_pzu_pt60` | 60 min | Current 60-minute interval price |

**Unit:** RON/MWh  
**State class:** `measurement` (compatible with Energy Dashboard history graphs)

### Attributes (on every sensor)

| Attribute | Description |
|---|---|
| `all_prices` | List of all prices for the day (96 / 48 / 24 values) |
| `min_price_ron_mwh` | Daily minimum price |
| `max_price_ron_mwh` | Daily maximum price |
| `avg_price_ron_mwh` | Daily average price |
| `current_interval_index` | 0-based index of the current interval |
| `source` | URL the data was fetched from |

---

## Installation via HACS (recommended)

1. Open **HACS** → **Integrations**
2. Click the three-dot menu (⋮) in the top-right corner → **Custom repositories**
3. Add `https://github.com/AdrianFasie/ha-opcom-pzu` with category **Integration**
4. Search for **OPCOM PZU** and click **Download**
5. Restart Home Assistant

## Manual installation

1. Copy the `custom_components/opcom_pzu/` folder into your HA config directory  
   (next to `configuration.yaml`)
2. Restart Home Assistant

---

## Configuration

After installation and restart:

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **OPCOM PZU**
3. Click **Submit** — HA will verify connectivity and create the integration

No YAML configuration is needed.

---

## Troubleshooting

### No prices / unavailable state
- Enable debug logging to see what the scraper found:
  ```yaml
  logger:
    logs:
      custom_components.opcom_pzu: debug
  ```
- The `current_interval_index` attribute tells you which row was selected.
- If the OPCOM page layout changes, the parser may need updating — please [open an issue](https://github.com/AdrianFasie/ha-opcom-pzu/issues).

### "Unable to connect" during setup
- Check that your HA instance can reach `www.opcom.ro` (no firewall/proxy blocking).

---

## Contributing

Pull requests welcome. Please open an issue first for any significant change.

## License

MIT
