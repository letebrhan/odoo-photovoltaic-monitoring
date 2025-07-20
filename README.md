# Odoo Photovoltaic Plant Monitoring

This Odoo module extends the `plants` management system to provide **comprehensive monitoring, analytics, and dashboards** for photovoltaic (PV) power plants. It enables real-time performance tracking, predictive analysis, and visual dashboards.

## Features

- Photovoltaic-specific fields and configurations
- Daily PR, irradiation, and energy computation
- Automatic JSX-based chart image export
- Performance vs PVGIS (expected) data comparison
- Default chart and dashboard creation for:
  - Dataloggers
  - Inverters
  - Stringboxes
  - Sensors
- Map and tree views with live inverter/sensor status
- Scheduled background computation of plant KPIs

## Usage

1. Add a plant of type "Plant::Photovoltaic".
2. Configure its sensor and inverter tasks.
3. Use buttons in the Config tab to:
   - Create default charts
   - Create dashboards
   - Define meter-inverter tables

## Cron Jobs

- `_get_daily_pr()` every 30 min
- `_compute_latest_pv_values()` every 1 min
- `_compute_latest_stringbox_values()` every 30 min

---

📈 Built for grid operators, energy analysts, and asset managers.
