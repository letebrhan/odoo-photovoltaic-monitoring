# Regenerate README.md and __manifest__.py files due to reset
readme_content = """# Odoo Photovoltaic Plant Monitoring

This Odoo module extends the plants management system to support photovoltaic (PV) power plants. It enables real-time performance tracking, predictive analysis, and visual dashboards.

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
"""

manifest_content = """{
    "name": "Odoo Photovoltaic Plant Monitoring",
    "version": "1.0",
    "summary": "Monitoring and visualization of photovoltaic plants",
    "category": "Energy",
    "author": "Letebrhan Alemayoh Siyum",
    "depends": ["ekogrid"],
    "data": [
        "plants_photovoltaic_view.xml"
    ],
    "installable": True,
    "application": True
}
"""

gitignore_content = """
# Python bytecode
__pycache__/
*.py[cod]
*.so
*.egg
*.egg-info
*.pyo

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs and editors
.vscode/
.idea/
*.sublime-project
*.sublime-workspace

# System files
.DS_Store
Thumbs.db

# Logs and dumps
*.log
*.sql
*.sqlite

# Odoo specific
*.zip
*.xlsx
*.xls
*.csv
*.pdf
*.png
*.jpg
*.jpeg

# Compiled assets (JSX/CSS)
static/src/jsx/*.js
static/src/css/*.css
"""

# Write these files
paths = {
    "/mnt/data/README.md": readme_content,
    "/mnt/data/__manifest__.py": manifest_content,
    "/mnt/data/.gitignore": gitignore_content
}

for path, content in paths.items():
    with open(path, "w") as f:
        f.write(content)

# Proceed to zip the regenerated files and cleaned Python files
cleaned_python_files = [
    "/mnt/data/plants_photovoltaic_cleaned.py",
    "/mnt/data/pv_plants_default_charts_creator_cleaned.py",
    "/mnt/data/pv_plants_default_dashboards_creator_cleaned.py"
]

zip_path = "/mnt/data/odoo_photovoltaic_monitoring_module.zip"
with zipfile.ZipFile(zip_path, 'w') as zipf:
    for file in list(paths.keys()) + cleaned_python_files:
        zipf.write(file, arcname=os.path.basename(file))

zip_path

