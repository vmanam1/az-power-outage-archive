# Arizona Power Outage Archive

An automated archival system that periodically collects and stores public power outage data from Arizona utility providers. The project creates timestamped JSON snapshots that preserve historical outage information for analysis, research, and visualization.

## Features

- Automated outage data collection
- Supports multiple utility providers
  - APS (Arizona Public Service)
  - SRP (Salt River Project)
  - TEP (Tucson Electric Power)
  - UES (UniSource Energy Services)
  - SSVEC (Sulphur Springs Valley Electric Cooperative)
  - Trico Electric Cooperative
  - Electrical District No. 3 (ED3)
  - Mohave Electric Cooperative
  - Navopache Electric Cooperative
- Timestamped JSON archives
- Standardized data format across providers
- Scheduled execution using GitHub Actions
- Automated tests on every push and pull request
- Source and snapshot data-quality validation
- GitHub issue alerts for scraper failures and recoveries
- Historical outage snapshots for long-term analysis

---

## Project Structure

```
az-power-outage-archive/
│
├── .github/
│   └── workflows/
│       └── scrape.yml
│
├── providers/
│   ├── aps.py
│   ├── srp.py
│   ├── tep.py
│   ├── ues.py
│   ├── ssvec.py
│   ├── nisc.py
│   ├── trico.py
│   ├── ed3.py
│   ├── mohave.py
│   ├── navopache.py
│   ├── base.py
│   └── __init__.py
│
├── scripts/
│   ├── run.py
│   ├── archive.py
│   ├── config.py
│   ├── logger.py
│   └── utils.py
│
├── data/
│   ├── aps/
│   ├── srp/
│   ├── tep/
│   ├── ues/
│   ├── ssvec/
│   ├── trico/
│   ├── ed3/
│   ├── mohave/
│   └── navopache/
│
├── requirements.txt
└── README.md
```

---

## Supported Providers and Sources

| Provider | Public outage website | Collection method |
|----------|-----------------------|-------------------|
| APS (Arizona Public Service) | [APS Outage Center](https://www.aps.com/en/Utility/Outage/Outage-Center) | ArcGIS REST API |
| SRP (Salt River Project) | [SRP Outages and Storm Safety](https://www.srpnet.com/customer-service/safety/outages-storm) | Public outage API |
| TEP (Tucson Electric Power) | [TEP Outages](https://www.tep.com/outages/) | Public outage API |
| UES (UniSource Energy Services) | [UES Electric Outage Map](https://www.uesaz.com/electric-outage-map/) | Public outage API |
| SSVEC (Sulphur Springs Valley Electric Cooperative) | [SSVEC Outage Center](https://www.ssvec.org/outage/) | ArcGIS REST API |
| Trico Electric Cooperative | [Trico Outage Map](https://ebill.trico.org/maps/Trico_External/OutageWebMap/) | NISC public map |
| Electrical District No. 3 (ED3) | [ED3 Outage Map](https://ww3.ed3online.org/OMSWebMap/OMSWebMap.htm) | Public XML outage service |
| Mohave Electric Cooperative | [Mohave Outage Map](https://ebill.mohaveelectric.com/maps/OutageWebMap/) | NISC public map |
| Navopache Electric Cooperative | [Navopache Outage Map](https://ebill1.navopache.org/maps/OutageWebMap/) | NISC public map |

### Collection Notes

- Snapshot timestamps and outage times are normalized to Arizona time (`MST`, UTC-7).
- Utilities may suppress small outages, delay updates, or omit fields for safety and privacy reasons.
- Trico, Mohave, and Navopache use NISC browser-based maps. Their collectors require Google Chrome and Selenium.
- ED3 provides an XML feed; APS and SSVEC provide ArcGIS feature layers; SRP provides JSON; TEP and UES provide JSON via a map feed API.
- Provider websites and response formats are controlled by the utilities and may change without notice.
- Temporary HTTP and browser failures are retried up to three times with exponential backoff.
- Each provider is isolated so successful snapshots are preserved when another provider fails.
- Snapshot metadata, timestamps, coordinates, customer counts, identifiers, and summary totals are validated before files are written.
- Malformed source counts are rejected rather than silently converted to zero. Structurally valid empty utility feeds remain valid zero-outage snapshots.
- The archive is historical reference data, not an emergency notification service. Always confirm current conditions on the utility's website.

---

## Output Format

Each archived snapshot follows a standardized structure.

```json
{
  "metadata": {
    "provider": "APS",
    "scraped_at": "2026-07-01 17:00:00 MST",
    "source": "APS ArcGIS REST API",
    "scraper_version": "1.0.0"
  },
  "summary": {
    "outage_count": 12,
    "customers_affected": 3158
  },
  "outages": [
    {
      "latitude": 33.45,
      "longitude": -111.95,
      "customers": 42,
      "cause": "Equipment Failure",
      "start_time": "2026-07-01 13:31 MST",
      "etr": "2026-07-01 21:00 MST"
    }
  ]
}
```

---

## Running Locally

Clone the repository

```bash
git clone https://github.com/vmanam1/az-power-outage-archive.git
cd az-power-outage-archive
```

Create a virtual environment

```bash
python -m venv venv
```

Activate it

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Google Chrome must be installed when collecting Trico, Mohave, or Navopache data.

Run the scraper

```bash
python -m scripts.run
```

Run the test suite

```bash
python -m unittest discover -s tests -v
```

---

## Automation

The project uses two GitHub Actions workflows:

- `scrape.yml` runs the scraper hourly at minute 7 and can also be started manually. Successful provider snapshots are committed even if another provider fails.
- `test.yml` runs the complete unit test suite on every push and pull request.

The scraper job has a 15-minute timeout. If a run fails, the workflow opens an `Outage archive workflow failure` issue or adds the failed run to the existing open alert. The next successful run comments with the recovery run and closes that issue automatically. This requires the workflow's scoped `issues: write` permission.

### Data-quality checks

Before a snapshot is archived, the collector verifies:

- Provider identity and Arizona MST timestamp metadata
- Non-negative outage and customer totals
- Agreement between summary totals and outage records
- Valid, complete coordinate pairs and record identifiers
- Valid MST timestamps for outage lifecycle fields
- Required provider customer counts without malformed-to-zero coercion

A provider that fails validation is reported as failed, while other providers continue and preserve their successful snapshots.

---

## Data

Archived outage snapshots are stored under

```
data/
├── aps/
├── srp/
├── tep/
├── ues/
├── ssvec/
├── trico/
├── ed3/
├── mohave/
└── navopache/
```

Each provider directory contains timestamped JSON snapshots generated during scheduled runs.

---

## Technologies

- Python
- Requests
- Selenium and Google Chrome for NISC outage maps
- GitHub Actions
- JSON
- REST APIs

---

## Local Visualization Dashboard

The repository includes a complete, lightweight dashboard called **Arizona Power Outage Explorer** that visualizes the archived JSON outage snapshots on an interactive Arizona map. It is designed to run smoothly on a local machine or a low-power single-board computer like a Raspberry Pi.

### Features
- **Interactive Map**: Centered on Arizona, utilizing Leaflet.js with marker clustering (`Leaflet.markercluster`) and circle markers scaled logarithmically according to customers affected.
- **Granular Filters**: Filter by utility provider, date boundaries, time-of-day ranges, customer count ranges, and search cause texts.
- **Multiple Display Modes**:
  - **Latest Data**: Shows only the newest available snapshot for each selected provider (default).
  - **Snapshot at Selected Time**: Looks up the snapshot at or immediately preceding a chosen date/time.
  - **Historical Observations**: Shows cumulative observations from all matching snapshots within a date range (records may repeat).
  - **Unique Outages**: Deduplicates historical observations using identifier fields (like `incident_id`, `pole_number`, `event`) or a geographical-temporal fallback.
- **Charts & Feed**: Displays responsive summary charts (affected customers by provider, count of records, timeline plot) and a sortable, paginated table of records.
- **CSV Data Export**: Download the active filtered dataset as a standard CSV format.
- **Auto-Refresh**: Polls the backend status every 60 seconds (configurable) and automatically updates data when new JSON files are added or modified, showing a browser notification without reloading the page.
- **Responsive & Accessible**: Support for responsive screens and a localized dark/light mode toggle.

### Installation & Run

1. Make sure Flask is installed:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the application:
   ```bash
   python app.py
   ```
   Or use the provided launcher script:
   ```bash
   ./scripts/start_dashboard.sh
   ```
3. Open the dashboard:
   - Locally: [http://localhost:5000](http://localhost:5000)
   - On LAN: `http://<pi-ip-address>:5000`

### Environment Variables

The application can be configured using environment variables (or by placing a `.env` file in the root):

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | IP to bind the server to. `0.0.0.0` exposes it to the local network (LAN). |
| `PORT` | `5000` | Port to run the server on. |
| `FLASK_DEBUG` | `false` | Enables debug mode when set to `true`. |
| `DATA_DIR` | `data` | Subdirectory containing provider snapshots. |
| `AUTO_REFRESH_SECONDS` | `60` | Frequency in seconds to check for new/modified snapshots. |

### Raspberry Pi Deployment (Optional Systemd Setup)

To configure the dashboard to run automatically as a background system service on your Raspberry Pi:

1. Copy the template service configuration file:
   ```bash
   cp deployment/az-outage-dashboard.service.example deployment/az-outage-dashboard.service
   ```
2. Open `deployment/az-outage-dashboard.service` in an editor and update:
   - `User`: Your Linux username (e.g. `pi`).
   - `WorkingDirectory`: The path to this repository.
   - `ExecStart`: The path to `scripts/start_dashboard.sh`.
3. Copy the modified service file to systemd:
   ```bash
   sudo cp deployment/az-outage-dashboard.service /etc/systemd/system/
   ```
4. Reload systemd, enable, and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable az-outage-dashboard.service
   sudo systemctl start az-outage-dashboard.service
   ```

### Troubleshooting & Safety Note

- **Internet Access**: The Leaflet map downloads its background map tiles from OpenStreetMap, which requires an active internet connection. The outage snapshot data itself is processed locally.
- **Security**: The web dashboard is meant for trusted local network environments. Exposing Flask directly to the public internet without an authenticating reverse proxy is not recommended.

---

## Disclaimer

This project archives publicly available outage information provided by Arizona utility companies. It is intended for research, educational, and historical purposes and is not affiliated with the listed utilities.

