# Arizona Power Outage Archive

Utilities show you outages on a live map, but once an outage clears, that information is gone — there's no public record of what happened, where, or for how long. This project keeps one.

Every hour a collector — a Raspberry Pi running on a systemd timer — polls nine Arizona electric utilities, normalizes their wildly different data formats into one shape, and commits a timestamped JSON snapshot to this repo. Over time that builds a searchable history of who lost power and when. A bundled Flask dashboard — the **Arizona Power Outage Explorer** — reads those snapshots straight off disk and turns them into a map, charts, a filterable table, and CSV export.

> [!IMPORTANT]
> This is a research and history tool, not an emergency service. Utility feeds can be delayed, incomplete, or down entirely, and this archive inherits all of those gaps. For anything that actually matters — reporting an outage, checking current status, staying safe — go to your utility's own site.

## The utilities

| Provider | Utility | Public map | How it's collected |
| --- | --- | --- | --- |
| `aps` | Arizona Public Service | [APS Outage Center](https://www.aps.com/en/Utility/Outage/Outage-Center) | ArcGIS REST API |
| `srp` | Salt River Project | [SRP Outages](https://www.srpnet.com/customer-service/safety/outages-storm) | JSON API |
| `tep` | Tucson Electric Power | [TEP Outages](https://www.tep.com/outages/) | Map feed API |
| `ues` | UniSource Energy Services | [UES Electric Outage Map](https://www.uesaz.com/electric-outage-map/) | Map feed API (shares TEP's backend) |
| `ssvec` | Sulphur Springs Valley Electric Cooperative | [SSVEC Outage Center](https://www.ssvec.org/outage/) | ArcGIS REST API |
| `trico` | Trico Electric Cooperative | [Trico Outage Map](https://trico.outagemap.coop/) | NISC hosted outage map (JSON) |
| `ed3` | Electrical District No. 3 | [ED3 Outage Map](https://ww3.ed3online.org/OMSWebMap/OMSWebMap.htm) | XML service |
| `mohave` | Mohave Electric Cooperative | [Mohave Outage Map](https://mohaveelectric.outagemap.coop/) | NISC hosted outage map (JSON) |
| `navopache` | Navopache Electric Cooperative | [Navopache Outage Map](https://navopache.outagemap.coop/) | NISC hosted outage map (JSON) |

Every provider hands out JSON or XML if you ask the right endpoint — including the three co-ops on NISC's platform (Trico, Mohave, Navopache), whose hosted outage maps read static JSON from `outagemap-data.cloud.coop`. Each outage there carries its coordinates as Web Mercator offsets from the map's configured extent, which the collector converts back to latitude/longitude (the decode matches the utilities' own map markers exactly). Earlier versions drove the legacy NISC maps with headless Chrome + Selenium; that dependency is gone.

## How collection works

Each provider is its own class under `providers/`, and they all share a small contract: fetch the source, shape it into a common outage record, and validate the result before it's allowed anywhere near the archive. Validation is deliberately strict — it checks that the provider name matches, timestamps parse as Arizona time, customer counts are non-negative integers, coordinates are finite and in range, the summary totals actually add up to the individual records, and that a record without coordinates at least carries some other identifier. A malformed value fails that one provider loudly rather than getting quietly coerced to zero and polluting the history.

The runner (`scripts/run.py`) fetches every provider in turn and keeps going if one blows up, so a single flaky endpoint never throws away the good snapshots from the other eight. It does exit non-zero at the end if any provider failed — but the collector commits the snapshots that did succeed first, and treats that exit code separately from whether the run is *healthy* (see [Automation](#automation)).

One snapshot is only written when a provider's outages have actually changed since the last one. An hour where nothing moved doesn't add a duplicate file — the runner compares the new outage payload against the most recent snapshot and skips the write if they match. All providers in a single run also share one timestamp, so a given run's files line up to the minute instead of drifting apart while the slower browser-based collectors finish.

## The dashboard

The Explorer reads the archive directly from the filesystem. There's no database and no import step — drop new snapshot files into `data/` and the app picks them up. It polls for changes in the background and reloads when the file count or newest modification time shifts.

### Map

An OpenStreetMap-backed Leaflet map centered on Arizona. Markers are colored by utility and sized (on a log scale) by customers affected, clustered when they're dense, and clickable for the full outage detail. Rows in the table below link back to their marker. Records that came in without usable coordinates can't be plotted, but they still count toward the totals and show up in the table so they don't silently vanish.

### Display modes

The same archive can be sliced four ways, depending on the question you're asking:

| Mode | What it shows | Good for |
| --- | --- | --- |
| **Latest Data** | The newest snapshot for each provider, independently. | A current statewide picture |
| **Snapshot at Selected Time** | For each provider, the newest snapshot at or before a time you pick. | Reconstructing a past moment |
| **Historical Observations** | Every matching record from every snapshot in a date range — the same incident reappears as it evolves. | Watching how outages changed |
| **Unique Outages** | Historical records deduplicated down to one row per incident, keeping the latest observation. | Counting distinct incidents |

Unique-outage matching keys off a real identifier when the provider gives one (`incident_id`, `pole_number`, or `event`), and falls back to provider + rounded coordinates + start time otherwise. It's a reasonable estimate, not a guarantee — two providers describe "the same outage" very differently, and some don't hand out stable IDs at all.

### Filters

You can narrow any mode by provider, snapshot date range, time-of-day window, customer-count range, and a text search across cause and comments. "Active only" hides anything with a restoration time, and there's a toggle for whether unknown/zero-customer records should ignore the count limits. Whatever you pick is written into the URL, so a filtered view is just a link you can bookmark or share.

### Charts, table, and export

Below the map are two per-provider breakdowns (customers affected and outage count) and a timeline of outages and customers over the matching snapshots. The table is searched, sorted, and paginated entirely in the browser, and there's a light/dark theme that sticks in local storage. **Export CSV** hands you exactly the filtered set you're looking at — provider, customer count, cause and comments, the outage lifecycle timestamps, coordinates, city/boundary, provider IDs, division, and snapshot time.

## Running it yourself

You'll need Python 3.11+ and `pip`. Live collection and the dashboard's map tiles both need internet; the archived JSON itself is read locally.

```bash
git clone https://github.com/vmanam1/az-power-outage-archive.git
cd az-power-outage-archive
python -m venv venv
```

Activate the virtual environment — PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

Then install and start the dashboard:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>. The server binds `0.0.0.0` by default, so another machine on the same trusted network can reach it at `http://<server-ip>:5000` if your firewall allows it. On macOS/Linux (or Git Bash on Windows) `./scripts/start_dashboard.sh` does the same thing, plus a couple of sanity checks.

To run a collection pass locally:

```bash
python -m scripts.run
```

And the tests, which is what CI runs:

```bash
python -m unittest discover -s tests -v
```

Dev-only tooling (pytest, black, flake8) lives in `requirements-dev.txt` if you want it.

## Configuration

Config comes from environment variables. `.env.example` documents them, but note that nothing in this project auto-loads a `.env` file — export the variables in your shell or set them in your service manager.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Bind address. Use `127.0.0.1` to keep it local-only. |
| `PORT` | `5000` | HTTP port. |
| `FLASK_DEBUG` | `false` | Flask debug mode. Never turn this on for anything reachable from outside. |
| `DATA_DIR` | `data` | Archive root, one subfolder per provider. Relative paths resolve from the working directory. |
| `AUTO_REFRESH_SECONDS` | `60` | How often the browser checks for new snapshot files. |

```powershell
$env:HOST = "127.0.0.1"; $env:PORT = "8080"; python app.py
```

```bash
HOST=127.0.0.1 PORT=8080 python app.py
```

## HTTP API

Everything reads from `DATA_DIR`. The dashboard is built on these, but they're plain JSON and fine to use on their own.

| Endpoint | Returns |
| --- | --- |
| `GET /api/health` | `{"status": "healthy"}` |
| `GET /api/file-status` | Snapshot file count and newest modification time (drives auto-refresh) |
| `GET /api/metadata` | Providers, date bounds, snapshot count, newest snapshot per provider, known causes, data-quality counts |
| `GET /api/outages` | Normalized outage records plus a summary for the current query |
| `GET /api/timeline` | Per-provider, per-snapshot outage and customer totals for charting |
| `GET /api/export.csv` | The filtered records as a streamed CSV |

`/api/outages`, `/api/timeline`, and `/api/export.csv` take the dashboard's filter parameters:

| Parameter | Format | Meaning |
| --- | --- | --- |
| `providers` | Comma-separated or repeated | e.g. `providers=aps,srp` |
| `display_mode` | `latest`, `snapshot_at_time`, `historical`, `unique_outages` | Which selection strategy to use |
| `snapshot_time` | Date/time | Target for `snapshot_at_time` |
| `start_date` / `end_date` | `YYYY-MM-DD` or full date/time | Snapshot range for the historical modes |
| `time_of_day_start` / `time_of_day_end` | `HH:MM` | Outage start-time window |
| `min_customers` / `max_customers` | Integer | Customer-count range |
| `cause` | Text | Case-insensitive substring match on cause and comments |
| `active_only` | `true` / `false` | Drop records that already have a restoration time |
| `include_unknown_customers` | `true` / `false` | Let zero/unknown counts skip the min/max limits |

```text
/api/outages?providers=aps,srp&display_mode=historical&start_date=2026-07-01&end_date=2026-07-07&min_customers=10&active_only=true
```

One quirk worth knowing: `/api/timeline` always aggregates across the snapshot date range regardless of `display_mode`, because a timeline only makes sense over time. So the chart can show history even while the map is in latest mode.

## Snapshot format

Files land under `data/<provider>/` named with the Arizona-local scrape time:

```text
data/aps/2026-07-18_17-02.json
```

A snapshot is metadata, a summary, and the outage list:

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
      "start_time": "2026-07-18 13:31:00 MST",
      "etr": "2026-07-18 21:00:00 MST"
    }
  ]
}
```

Which fields an outage carries depends on the source. Beyond the ones above you'll see `comments`, `restored_time`, `last_update`, `city`, `boundary`, `incident_id`, `pole_number`, `event`, `division`, and `customers_restored` when a utility provides them.

Most of Arizona doesn't observe daylight saving, so every timestamp is normalized to Arizona time and labeled `MST` (UTC-7), and that's what the dashboard's comparisons and display modes run on.

When the dashboard reads old files it's forgiving: unparseable JSON is skipped and counted in the metadata rather than crashing the request, and missing or invalid coordinates are tracked separately so you can see the data's rough edges. Parsed snapshots are cached by file modification time and the whole scan is memoized against a directory fingerprint, so flipping between filters doesn't re-read the entire archive every time.

## Automation

Collection and CI live in two different places.

**Hourly collection runs on a Raspberry Pi.** A systemd timer (`deploy/systemd/outage-archive.timer`) fires at minute 7 of every hour and runs `scripts/collect.sh`, which scrapes all nine providers, commits whatever new snapshots came out of the run, and pushes them to GitHub over SSH using a repo deploy key. The snapshots therefore live in two places — on the Pi and in this repo. If a push is rejected because the remote moved, the script rebases and retries so the Pi never ends up diverged, and `Persistent=true` on the timer means a run missed while the Pi was off is picked up as soon as it's back. Because the collector commits before it inspects the exit code, the snapshots from providers that succeeded still get committed even when one collector (typically a browser-based NISC co-op whose server is hanging) takes the overall run's exit code non-zero.

**Failure alerting is a dead-man's-switch**, not a per-failure alarm. On each run the collector pings a [healthchecks.io](https://healthchecks.io) check — a success ping when it ran and pushed, a failure ping if the push couldn't complete. The ping is deliberately independent of whether any single utility was reachable, so an upstream outage never raises a false alarm; you only get an email when a ping actually goes *missing*, i.e. the Pi itself stopped collecting (offline, hung, disk full, broken credentials). The ping URL is injected from a private, uncommitted env file on the Pi (`/etc/default/outage-archive`) rather than stored in this public repo.

**GitHub Actions still runs the tests** — `.github/workflows/test.yml` runs the full unittest suite on every push and pull request. The collection workflow (`.github/workflows/scrape.yml`) is kept as a manual fallback: its hourly `schedule` is commented out so it doesn't race the Pi for commits, but it can still be triggered by hand from the Actions tab, and re-enabling the cron restores Actions-based collection. In that mode it opens (or comments on) a GitHub issue titled **Outage archive workflow failure** and closes it on the next healthy run.

## Running on a Raspberry Pi

A Pi (or any small Linux box) is enough to run both the collector and the dashboard. In the live setup the Pi is the collector.

### The collector

This is what actually produces the archive — plain Python and HTTP, no browser required. Clone the repo, create a venv, install `requirements.txt`, and give the Pi push access with a repo **deploy key** — an SSH key added under the repo's Settings → Deploy keys with write access.

Sample units live in `deploy/systemd/`. The service sets the venv interpreter and an optional private env file for the healthchecks ping; edit the `User=` and hard-coded paths to match your layout:

```bash
# point git at the deploy key and use SSH
git remote set-url origin git@github.com:vmanam1/az-power-outage-archive.git
git config core.sshCommand "ssh -i ~/.ssh/id_ed25519_ghdeploy -o IdentitiesOnly=yes"

# optional: dead-man's-switch ping URL, kept out of the repo
echo 'HEALTHCHECK_URL=https://hc-ping.com/<your-uuid>' | sudo tee /etc/default/outage-archive

sudo cp deploy/systemd/outage-archive.service deploy/systemd/outage-archive.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now outage-archive.timer
```

Check on it with `systemctl status outage-archive.service`, `systemctl list-timers outage-archive.timer`, and `journalctl -u outage-archive.service`. While a provider's upstream is down the service will report `failed` (non-zero exit) even though the healthy providers still committed — that's cosmetic; the dead-man's-switch, not the exit code, is the real signal.

### The dashboard

Optional, and independent of the collector — it only *reads* the archive, so it can run on the Pi or anywhere else. There's a sample unit at `deployment/az-outage-dashboard.service.example`:

```bash
cp deployment/az-outage-dashboard.service.example deployment/az-outage-dashboard.service
# edit User, WorkingDirectory, and ExecStart for your setup
sudo cp deployment/az-outage-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now az-outage-dashboard.service
```

Check on it with `systemctl status az-outage-dashboard.service` and `journalctl -u az-outage-dashboard.service -f`.

That said, `app.py` runs Flask's development server, which is fine on a trusted network but not something to expose directly. If you're putting it on the public internet, front it with a real WSGI server behind an HTTPS reverse proxy, add whatever access control makes sense, and — again — leave debug mode off.

## Project layout

```text
az-power-outage-archive/
├── .github/workflows/   # Test CI + fallback collection workflow
├── dashboard/           # Archive scanning, caching, normalization, filters
├── data/                # The snapshots, grouped by provider
├── deploy/systemd/      # Pi collector: systemd service + hourly timer
├── deployment/          # Example dashboard systemd unit
├── providers/           # One collector per utility + shared validation
├── scripts/             # Runner, Pi collector (collect.sh), HTTP retry, archive writer, launcher
├── static/              # Dashboard CSS and JavaScript
├── templates/           # Flask HTML
├── tests/               # Collector, validation, archive-reader, and API tests
└── app.py               # Flask dashboard and API
```

## Built with

Python and Flask on the backend; Requests for all nine collectors. The frontend is vanilla JavaScript with Leaflet (and markercluster) for the map and Chart.js for the charts. A Raspberry Pi on a systemd timer runs the hourly collection (with GitHub Actions as a manual fallback), GitHub Actions runs CI, healthchecks.io watches the collector, and the archive itself is just JSON in Git.

## Known limits

This can only preserve what utilities choose to publish — they routinely round customer counts, generalize locations, or leave small incidents off the map entirely, and none of that is recoverable after the fact. Public endpoints also change without warning and occasionally break a collector until it's fixed. Keep in mind that a historical-mode row is an observation at a snapshot, not necessarily a distinct outage; unique mode does its best to reconcile them but won't be perfect. And a zero customer count can mean a genuine zero or just missing source data, since normalization treats both the same way.

## Contributing

PRs welcome. If you touch a collector, add or update tests with mocked responses — tests should never hit live utility endpoints. If you touch the dashboard, keep the API tests passing and sanity-check the latest, historical, point-in-time, and unique-outage paths. Run the suite before you open a PR:

```bash
python -m unittest discover -s tests -v
```

## Disclaimer

This is an independent archive of publicly available information, built for research, education, and history. It isn't affiliated with, endorsed by, or operated by any of the utilities listed, and it makes no promises about completeness, accuracy, or timeliness. For current conditions, outage reporting, and anything urgent, use official utility and emergency channels.
