# Arizona Power Outage Archive

An automated archival system that periodically collects and stores public power outage data from Arizona utility providers. The project creates timestamped JSON snapshots that preserve historical outage information for analysis, research, and visualization.

## Features

- Automated outage data collection
- Supports multiple utility providers
  - APS (Arizona Public Service)
  - SRP (Salt River Project)
  - TEP (Tucson Electric Power)
  - UES (UniSource Energy Services)
- Timestamped JSON archives
- Standardized data format across providers
- Scheduled execution using GitHub Actions
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
│   └── ues/
│
├── requirements.txt
└── README.md
```

---

## Supported Providers

| Provider | Status |
|----------|--------|
| APS (Arizona Public Service) | ✅ Supported |
| SRP (Salt River Project) | ✅ Supported |
| TEP (Tucson Electric Power) | ✅ Supported |
| UES (UniSource Energy Services) | ✅ Supported |

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

Run the scraper

```bash
python -m scripts.run
```

---

## Automation

The project uses GitHub Actions to automatically execute the scraper on a scheduled interval and archive new outage snapshots.

---

## Data

Archived outage snapshots are stored under

```
data/
├── aps/
├── srp/
├── tep/
└── ues/
```

Each provider directory contains timestamped JSON snapshots generated during scheduled runs.

---

## Technologies

- Python
- Requests
- GitHub Actions
- JSON
- REST APIs

---

## Disclaimer

This project archives publicly available outage information provided by Arizona utility companies. It is intended for research, educational, and historical purposes and is not affiliated with APS, SRP, TEP, or UES.
