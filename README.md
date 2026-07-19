# Arizona Power Outage Archive

An automated archive and interactive web dashboard for public electric outage data across Arizona.

The project collects outage information from nine utility providers, validates and normalizes each response, and stores timestamped JSON snapshots in Git. The included **Arizona Power Outage Explorer** turns those snapshots into an interactive map, historical charts, searchable records, and downloadable CSV data.

> [!IMPORTANT]
> This is a historical and research tool, not an emergency notification service. Utility data may be delayed, incomplete, generalized, or temporarily unavailable. For current outage information and safety guidance, always use the utility provider's official website.

## What the project provides

- Hourly collection through GitHub Actions
- Nine Arizona electric utility providers in one normalized archive
- Timestamped, human-readable JSON snapshots
- Validation of provider metadata, counts, coordinates, timestamps, identifiers, and summary totals
- Retry handling for temporary HTTP and browser failures
- Provider isolation, so one failed source does not discard successful snapshots from other sources
- Automatic GitHub issue alerts when collection fails and recovery notices when it succeeds again
- An interactive dashboard for current and historical exploration
- Filters for provider, date, time of day, customer count, cause/comments, and outage status
- Latest, point-in-time, historical observation, and deduplicated outage views
- Clustered map markers, provider summaries, and historical charts
- Searchable, sortable, paginated outage records
- CSV export of the active filtered result set
- Automatic detection of new or modified snapshot files
- A documented JSON API for programmatic access
- Unit tests on every push and pull request

## Supported utilities

| Provider | Utility | Public source | Collection method |
| --- | --- | --- | --- |
| `aps` | Arizona Public Service | [APS Outage Center](https://www.aps.com/en/Utility/Outage/Outage-Center) | ArcGIS REST API |
| `srp` | Salt River Project | [SRP Outages and Storm Safety](https://www.srpnet.com/customer-service/safety/outages-storm) | Public JSON API |
| `tep` | Tucson Electric Power | [TEP Outages](https://www.tep.com/outages/) | Public map feed API |
| `ues` | UniSource Energy Services | [UES Electric Outage Map](https://www.uesaz.com/electric-outage-map/) | Public map feed API |
| `ssvec` | Sulphur Springs Valley Electric Cooperative | [SSVEC Outage Center](https://www.ssvec.org/outage/) | ArcGIS REST API |
| `trico` | Trico Electric Cooperative | [Trico Outage Map](https://ebill.trico.org/maps/Trico_External/OutageWebMap/) | NISC browser-rendered map |
| `ed3` | Electrical District No. 3 | [ED3 Outage Map](https://ww3.ed3online.org/OMSWebMap/OMSWebMap.htm) | Public XML service |
| `mohave` | Mohave Electric Cooperative | [Mohave Outage Map](https://ebill.mohaveelectric.com/maps/OutageWebMap/) | NISC browser-rendered map |
| `navopache` | Navopache Electric Cooperative | [Navopache Outage Map](https://ebill1.navopache.org/maps/OutageWebMap/) | NISC browser-rendered map |

Trico, Mohave, and Navopache require Selenium and Google Chrome because their NISC outage cards are rendered in a browser. The other collectors read public JSON, XML, or ArcGIS endpoints directly.

## Dashboard

The Arizona Power Outage Explorer reads the archive directly from disk. It does not require a database or a separate ingestion process: adding or updating snapshot files is enough for the application to see new data.

### Overview cards and data status

The top-level summary shows the records and customers represented by the current filters, the number of selected providers and snapshot files, and the visible time range. Archive metadata also reports malformed files and missing or invalid coordinates so data-quality limitations remain visible.

### Interactive map

- Centers on Arizona and uses OpenStreetMap background tiles
- Groups dense records with Leaflet marker clustering
- Colors records by utility provider
- Scales circle markers according to customers affected
- Displays outage details in marker popups
- Connects table rows to their map markers for quick navigation
- Continues to include records without usable coordinates in totals and the table, even though they cannot be placed on the map

### Display modes

| Mode | Behavior | Best used for |
| --- | --- | --- |
| **Latest Data** | Selects the newest available snapshot independently for each provider. | A current statewide overview |
| **Snapshot at Selected Time** | Selects, for each provider, the newest snapshot at or before the requested time. | Reconstructing conditions at a past moment |
| **Historical Observations** | Includes every matching record from every snapshot in the date range. The same incident can appear more than once as it changes over time. | Studying observations and archive activity |
| **Unique Outages** | Deduplicates historical records and retains the latest matching observation for each inferred incident. | Estimating distinct incidents in a period |

Unique-outage matching uses a provider record's `incident_id`, `pole_number`, or `event` when available. Otherwise, it falls back to a combination of provider, rounded coordinates or location, and start time. It is a practical archive-level estimate rather than a universal outage identity guarantee.

### Filters

The dashboard can filter the selected mode by:

- One or more utility providers
- Snapshot date range
- Outage start-time range within the day
- Minimum and maximum customers affected
- Cause or comments text
- Active outages only, where no restoration time is present
- Records with unknown/zero customer counts, optionally bypassing the customer-range limits

Active filter choices are reflected in the page URL, making filtered dashboard views bookmarkable and shareable.

### Charts and records

The visualization area contains:

- Customers affected by provider
- Visible outage records by provider
- A timeline of outage records and customers affected across matching snapshots
- A client-side searchable and sortable table
- Configurable table page sizes and pagination
- Clickable rows that focus the associated map marker
- Light and dark themes saved in browser storage

### CSV export

**Export CSV** downloads the same filtered dataset currently requested by the dashboard. Exported columns include provider, customers affected, cause, comments, outage lifecycle times, coordinates, city/boundary information, provider identifiers, division, and snapshot time.

## Quick start

### Requirements

- Python 3.11 or newer
- `pip`
- Google Chrome if you intend to run the Trico, Mohave, or Navopache collectors
- Internet access for live collection and for the dashboard's externally hosted map tiles and frontend libraries

Clone the repository and enter its directory:

```bash
git clone https://github.com/vmanam1/az-power-outage-archive.git
cd az-power-outage-archive
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Or activate it on macOS/Linux:

```bash
source venv/bin/activate
```

Install the runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

### Start the dashboard

Run Flask directly:

```bash
python app.py
```

On macOS/Linux, or from a Bash-compatible Windows shell, you can instead use:

```bash
./scripts/start_dashboard.sh
```

Then open [http://localhost:5000](http://localhost:5000). Because the default host is `0.0.0.0`, another device on the same trusted network can use `http://<server-ip>:5000` if the host firewall allows it.

### Run a collection locally

```bash
python -m scripts.run
```

Each provider is collected independently. If any provider fails, the command exits unsuccessfully after attempting all providers; valid snapshots from successful providers are still preserved.

### Run tests

The continuous-integration workflow uses Python's built-in `unittest` runner:

```bash
python -m unittest discover -s tests -v
```

Optional development tools are listed separately:

```bash
python -m pip install -r requirements-dev.txt
```

## Configuration

The dashboard reads configuration from environment variables. `.env.example` is a reference file; Flask does not load `.env` files automatically in this project, so export the variables in your shell or configure them through your service manager.

| Variable | Default | Description |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Address to bind. Use `127.0.0.1` for local-only access. |
| `PORT` | `5000` | HTTP port used by the Flask server. |
| `FLASK_DEBUG` | `false` | Enables Flask debug mode when set to `true`. Do not enable it on an exposed host. |
| `DATA_DIR` | `data` | Archive root containing one subdirectory per provider. Relative paths are resolved from the working directory. |
| `AUTO_REFRESH_SECONDS` | `60` | Browser polling interval for detecting new or modified JSON files. |

PowerShell example:

```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "8080"
python app.py
```

macOS/Linux example:

```bash
HOST=127.0.0.1 PORT=8080 python app.py
```

## HTTP API

All endpoints read from the configured `DATA_DIR`.

| Endpoint | Response |
| --- | --- |
| `GET /api/health` | Basic process health: `{"status": "healthy"}` |
| `GET /api/file-status` | JSON snapshot file count and newest modification time; used by auto-refresh |
| `GET /api/metadata` | Providers, archive date bounds, snapshot count, newest snapshot per provider, known causes, and data-quality counts |
| `GET /api/outages` | Normalized outage records plus summary totals for the active query |
| `GET /api/timeline` | Per-provider, per-snapshot outage and customer totals for charting |
| `GET /api/export.csv` | Streamed CSV containing the filtered outage records |

### Query parameters

`/api/outages`, `/api/timeline`, and `/api/export.csv` accept the dashboard's filter parameters:

| Parameter | Format | Meaning |
| --- | --- | --- |
| `providers` | Repeated values or comma-separated names | Provider selection, such as `providers=aps&providers=srp` |
| `display_mode` | `latest`, `snapshot_at_time`, `historical`, or `unique_outages` | Snapshot-selection strategy |
| `snapshot_time` | Date/time string | Target for `snapshot_at_time`; selects the nearest prior snapshot per provider |
| `start_date` | `YYYY-MM-DD` or date/time | Beginning of the snapshot range for historical modes |
| `end_date` | `YYYY-MM-DD` or date/time | End of the snapshot range for historical modes |
| `time_of_day_start` | `HH:MM` | Earliest outage start time to include |
| `time_of_day_end` | `HH:MM` | Latest outage start time to include |
| `min_customers` | Integer | Minimum customers affected |
| `max_customers` | Integer | Maximum customers affected |
| `cause` | Text | Case-insensitive substring search across cause and comments |
| `active_only` | `true` or `false` | Excludes records with a restoration time when true |
| `include_unknown_customers` | `true` or `false` | Allows zero/unknown counts to bypass min/max limits |

Example:

```text
/api/outages?providers=aps,srp&display_mode=historical&start_date=2026-07-01&end_date=2026-07-07&min_customers=10&active_only=true
```

The timeline endpoint always aggregates matching historical snapshots so the chart can show change over time, even when the primary outage view is in latest mode.

## Archive format

Snapshots are stored under `data/<provider>/` with Arizona-local filenames such as:

```text
data/aps/2026-07-18_17-02.json
```

A typical snapshot looks like this:

```json
{
  "metadata": {
    "provider": "APS",
    "scraped_at": "2026-07-18 17:02:00 MST",
    "source": "APS ArcGIS REST API",
    "scraper_version": "1.0.0"
  },
  "summary": {
    "outage_count": 2,
    "customers_affected": 447
  },
  "outages": [
    {
      "latitude": 33.45,
      "longitude": -111.95,
      "customers": 42,
      "cause": "Equipment Failure",
      "start_time": "2026-07-18 13:31 MST",
      "etr": "2026-07-18 21:00 MST"
    }
  ]
}
```

Provider records can contain additional fields including `comments`, `restored_time`, `last_update`, `city`, `boundary`, `incident_id`, `pole_number`, `event`, `division`, and `customers_restored`. Availability depends on the source utility.

### Time handling

Arizona does not observe daylight saving time in most of the state. Archive timestamps are normalized to Arizona time and labeled `MST` (UTC-7). Dashboard comparisons and display modes use these normalized snapshot timestamps.

### Data-quality behavior

Before writing a snapshot, the collectors validate:

- Provider identity and metadata
- Arizona timestamp structure
- Non-negative outage and customer totals
- Agreement between summary totals and individual outage records
- Required record identifiers where applicable
- Complete, finite, in-range coordinate pairs
- Supported outage lifecycle timestamps
- Provider customer counts without silently turning malformed source values into zero

Structurally valid empty feeds remain valid zero-outage snapshots. Malformed source values cause that provider to fail, while the other providers continue.

When the dashboard reads historical files, malformed JSON is skipped and reported in metadata. Missing or invalid coordinates are tracked separately. Snapshot contents are cached using file modification time and size, which keeps repeated dashboard queries responsive while still noticing changed files.

## Automation and monitoring

Two workflows live in `.github/workflows/`:

- **Archive Arizona Power Outages** runs at minute 7 of every hour and supports manual dispatch. GitHub schedule execution can be delayed during periods of high Actions load.
- **Test** runs the complete unit test suite on every push and pull request.

The archive job installs Chrome, runs all providers, stages `data/`, and commits any new snapshots. Its concurrency group prevents two archive jobs from racing on the same branch.

If collection fails, the workflow opens an issue named **Outage archive workflow failure**, or appends the latest run to the existing alert. The next successful run adds a recovery comment and closes the alert. Successful provider data is committed even when another provider caused the overall run to fail.

## Raspberry Pi and Linux service

The dashboard is lightweight enough for a Raspberry Pi or another small Linux host. A sample systemd unit is provided at `deployment/az-outage-dashboard.service.example`.

1. Clone the repository, create a virtual environment, and install the dependencies.
2. Copy the example unit:

   ```bash
   cp deployment/az-outage-dashboard.service.example deployment/az-outage-dashboard.service
   ```

3. Edit `User`, `WorkingDirectory`, and `ExecStart` for the actual account and repository path. Adjust the environment settings if needed.
4. Install and start the unit:

   ```bash
   sudo cp deployment/az-outage-dashboard.service /etc/systemd/system/az-outage-dashboard.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now az-outage-dashboard.service
   ```

5. Inspect its status and logs:

   ```bash
   systemctl status az-outage-dashboard.service
   journalctl -u az-outage-dashboard.service -f
   ```

The included Flask development server is appropriate for local and trusted-network use. For public access, place the application behind a production WSGI server and a properly configured HTTPS reverse proxy. Add authentication or network access controls as appropriate; never expose Flask debug mode publicly.

## Project layout

```text
az-power-outage-archive/
|-- .github/workflows/       # Hourly collection and test automation
|-- dashboard/               # Archive scanning, caching, normalization, and filters
|-- data/                    # Timestamped snapshots grouped by provider
|-- deployment/              # Example systemd service
|-- providers/               # Provider-specific collectors and shared validation
|-- scripts/                 # Collector runner, HTTP helpers, archiving, and launcher
|-- static/                  # Dashboard CSS and browser-side JavaScript
|-- templates/               # Flask HTML templates
|-- tests/                   # Scraper, validation, archive reader, and API tests
|-- app.py                   # Flask dashboard and API
|-- requirements.txt         # Runtime dependencies
`-- requirements-dev.txt     # Optional development tools
```

## Technology stack

- Python and Flask
- Requests for HTTP-based collectors
- Selenium and Google Chrome for browser-rendered NISC maps
- Leaflet, Leaflet.markercluster, and OpenStreetMap for mapping
- Chart.js for dashboard charts
- Vanilla JavaScript and CSS for the dashboard interface
- GitHub Actions for hourly collection and continuous integration
- JSON for the durable archive format

## Limitations

- The archive can only preserve what utilities publish; providers may suppress small incidents or omit precise locations and customer counts.
- Public endpoints and page structures can change without notice and may temporarily break a collector.
- A record in historical mode is an observation at a snapshot time, not necessarily a distinct outage.
- Unique-outage mode uses best-effort identifiers and may merge or separate records imperfectly.
- Zero customer counts can mean either a reported zero or unavailable/unknown source data after dashboard normalization.
- Map tiles and frontend CDN assets require Internet access, although archived outage JSON is read locally.
- The dashboard is intended for exploration, not operational dispatch, emergency response, or guaranteed real-time monitoring.

## Contributing

Contributions are welcome. For collector changes, include or update focused tests using mocked source responses; do not make unit tests depend on live utility endpoints. For dashboard changes, preserve the API tests and verify latest, historical, point-in-time, and unique-outage behavior where relevant.

Before opening a pull request, run:

```bash
python -m unittest discover -s tests -v
```

## Disclaimer

This project independently archives publicly available information for research, education, and historical analysis. It is not affiliated with, endorsed by, or operated by any utility listed above. No guarantee is made regarding completeness, accuracy, timeliness, availability, or suitability for any particular purpose.

Use official utility channels and emergency services for current conditions, outage reporting, hazards, and urgent assistance.
