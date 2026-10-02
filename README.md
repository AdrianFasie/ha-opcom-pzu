# OPCOM PZU — Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/AdrianFasie/ha-opcom-pzu.svg)](https://github.com/AdrianFasie/ha-opcom-pzu/releases)
[![License](https://img.shields.io/github/license/AdrianFasie/ha-opcom-pzu.svg)](LICENSE)

Track Romania's **day-ahead electricity market (PZU)** prices directly in Home Assistant.  
Data is fetched from [opcom.ro](https://www.opcom.ro/grafice-ip-raportPIP-si-volumTranzactionat/ro) via the PT15 XML export and updated every 15 minutes.

---

## Sensor

One sensor is created: **`sensor.opcom_pzu`**

| Property | Value |
|---|---|
| State | Price in RON/MWh for the current 15-min interval |
| Unit | RON/MWh |
| Update interval | Every 15 minutes |
| State class | `measurement` |

### Attributes

| Attribute | Description |
|---|---|
| `current_interval` | Human-readable interval, e.g. `14:00–14:15` |
| `price_date` | Date the current prices cover |
| `today_prices` | `{"00:00": 977.08, "00:15": 983.58, …}` — all 96 intervals |
| `tomorrow_available` | `true` once next-day prices are published |
| `tomorrow_date` | Date of tomorrow's prices |
| `tomorrow_prices` | Same format as `today_prices`, available from ~12:00–18:00 |
| `statistic_id` | `opcom_pzu:pzu_price` — use this in the statistics-graph card |

### Statistics (future prices on the graph)

The integration writes all 96 (and tomorrow's 96) prices directly into the HA statistics database with their exact timestamps. This means you can see **both past and future prices** on a single graph using the `statistics-graph` Lovelace card:

```yaml
type: statistics-graph
entities:
  - opcom_pzu:pzu_price
period: day
stat_types:
  - mean
title: PZU Electricity Price (RON/MWh)
```

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
3. Click **Submit** — HA verifies connectivity and creates the integration

No YAML configuration needed.

---

## How tomorrow's prices are loaded

OPCOM publishes next-day prices between approximately 12:00 and 15:00 Romania time. The integration polls for them every 15 minutes in the 12:00–18:00 window (extended as a safety net). As soon as prices appear they are injected into the statistics database and become visible on the graph.

---

## Troubleshooting

### Sensor unavailable or no prices
Enable debug logging:
```yaml
logger:
  logs:
    custom_components.opcom_pzu: debug
```
This shows how many XML entries were parsed and how many statistics were injected.

### "Unable to connect" during setup
Check that your HA instance can reach `www.opcom.ro` (no firewall or proxy blocking outbound HTTPS).

---

## Contributing

Pull requests welcome. Please open an issue first for any significant change.

## License

MIT
