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

## Disclaimer

This project archives publicly available outage information provided by Arizona utility companies. It is intended for research, educational, and historical purposes and is not affiliated with the listed utilities.
