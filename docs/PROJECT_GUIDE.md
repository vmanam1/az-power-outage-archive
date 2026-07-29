# Arizona Power Outage Archive — Project Guide

*A complete reference for anyone joining this project — including readers with no technical background. Last updated: July 27, 2026.*

---

## 1. What this project is (in plain English)

Electric utilities in Arizona show live outage maps on their websites: where the power is out, how many customers are affected, and when it might be restored. But the moment an outage is fixed, that information **disappears forever** — utilities don't publish history.

This project fixes that. Once every hour, a small computer (a Raspberry Pi) automatically visits eleven Arizona utilities' outage feeds, saves what they're reporting into small data files, and uploads copies to the internet (GitHub). Over weeks and months this builds a permanent, searchable history of power outages across Arizona — who lost power, where, when, why, and for how long.

A companion **website (the "dashboard")** turns those saved files into an interactive map, charts, and tables that anyone can explore in a web browser.

> **Important:** this is a research/history tool, not an emergency service. For a real outage, always use the utility's own website.

---

## 2. The system at a glance

```
  Eleven utility websites serving Arizona (APS, SRP, TEP, ...)
                     │
                     ▼   every hour, at 7 minutes past
        ┌─────────────────────────┐
        │  Raspberry Pi           │   "the collector"
        │  (leaps-rpi-1)          │
        │  - reads all 11 feeds    │
        │  - saves JSON files     │──────► copy #1: stored on the Pi itself
        │  - uploads to GitHub    │──────► copy #2: github.com/vmanam1/az-power-outage-archive
        │  - runs the dashboard   │──────► http://10.203.49.199:5000  (campus network only)
        └─────────────────────────┘
                     │
                     ▼  after every successful run
        healthchecks.io  ──► emails vmanam1@asu.edu ONLY if runs stop arriving
```

Three ideas to hold onto:

1. **The Raspberry Pi does everything.** It collects the data, stores it, uploads it, and serves the dashboard. It needs no human attention — every part restarts itself after crashes or power cuts.
2. **The data lives in two places** — on the Pi and on GitHub — so losing either one loses nothing.
3. **Silence means healthy.** You only get an email when something is genuinely wrong.

---

## 3. The eleven utilities we track

| Code | Utility | How we read it |
| --- | --- | --- |
| `aps` | Arizona Public Service | ArcGIS REST API (JSON) |
| `srp` | Salt River Project | JSON API |
| `tep` | Tucson Electric Power | Map feed API (JSON) |
| `ues` | UniSource Energy Services | Same backend as TEP |
| `ssvec` | Sulphur Springs Valley Electric Coop | ArcGIS REST API (JSON) |
| `trico` | Trico Electric Cooperative | NISC hosted outage map (JSON) |
| `ed3` | Electrical District No. 3 | XML service |
| `mohave` | Mohave Electric Cooperative | NISC hosted outage map (JSON) |
| `navopache` | Navopache Electric Cooperative | NISC hosted outage map (JSON) |
| `dixie` | Dixie Power (AZ Strip corner; UT filtered) | NISC hosted outage map (JSON) |
| `garkane` | Garkane Energy (AZ Strip; UT filtered) | NISC hosted outage map (JSON) |

All eleven are read with plain web requests — no browser automation anywhere. Each utility has its own small reader ("provider") in the `providers/` folder of the code, and every record passes strict validation before it's allowed into the archive (bad data fails loudly rather than being silently saved wrong).

---

## 4. What we built — progress log

### Phase 1 — Original setup (before July 24, 2026)
- Collection ran in the cloud on **GitHub Actions** (GitHub's free automation service), hourly.
- Three co-ops (Trico, Mohave, Navopache) were read by driving an invisible Chrome browser with Selenium — slow (minutes per run) and fragile.
- The Flask dashboard existed but wasn't deployed anywhere.

### Phase 2 — Move to the Raspberry Pi (July 24)
- Hourly collection moved from GitHub Actions to the Pi, run by a **systemd timer** (the Linux equivalent of an alarm clock) firing at 7 minutes past every hour. The GitHub Actions schedule was switched off (kept as a manual backup).
- The Pi pushes data to GitHub using a **deploy key** — a machine-only password that can write to this one repository and nothing else.
- **Monitoring** added: after every successful run the Pi "checks in" with healthchecks.io. If check-ins stop (Pi offline, crashed, disk full), healthchecks.io emails `vmanam1@asu.edu`. A single utility's website being down does *not* trigger an alarm — only a genuine collector stoppage does. (We proved this design the same week when Navopache's website went down for two days: the other eight utilities kept archiving and no false alarms fired.)
- The archive switched to keeping **one snapshot per provider every hour** even when nothing changed — a regular heartbeat of data is easier to analyze than gaps.

### Phase 3 — Better data and a better dashboard (July 26–27)
- **Derived regions:** most utilities don't say which town an outage is in, but all of them give coordinates. The dashboard now looks up the nearest Arizona town (from the US Census place list, fully offline) and shows it as "**≈ Marana**" — the ≈ marks it as an estimate, distinct from utility-published names.
- **Co-op upgrade — the big one:** we discovered the three NISC co-ops publish clean JSON behind their newer `outagemap.coop` sites. The collectors were rewritten to read it directly. Results: real customer counts for Mohave (previously always 0), outage causes and crew comments for Navopache and Trico, real ETRs when given, runs took seconds instead of minutes, and **Selenium/Chrome was removed from the project entirely**.
- **Dashboard redesign:** minimal flat design, one accent color, light/dark theme with a matching CARTO basemap, six charts (customers by provider, outages by provider, top causes with all "weather" spellings merged, active vs. restored, outage starts by hour, timeline), a polished table (consistent date/time cells, tinted provider chips), and honest empty-cell wording: *"Not specified"* for missing causes, *"ETR not specified by provider"* for missing restoration times.
- **Reliability finishers:** the dashboard became a systemd service too (auto-restarts on crash, starts on boot — verified by killing it and watching it come back), stale-browser-cache bugs were eliminated, and the README was rewritten to match reality.

**Current status: fully autonomous.** The system has run unattended for days — collecting, uploading, self-restarting, and staying silent because nothing is wrong.

---

## 5. How to check everything is working (no technical skills needed)

Any one of these three checks is enough:

1. **Look at GitHub.** Open <https://github.com/vmanam1/az-power-outage-archive/commits/main>. You should see a commit titled *"Archive outage snapshot … (rpi)"* about once per hour. If the newest one is less than ~2 hours old, collection is healthy.
2. **Open the dashboard** (must be on the campus network): <http://10.203.49.199:5000>. If the page loads and the "last checked" clock ticks, the dashboard is healthy.
3. **Check your email.** healthchecks.io emails `vmanam1@asu.edu` if the collector misses its hourly check-in. **No email = everything is fine.** (You can also log into healthchecks.io and see the check `az-outage-pi` showing green.)

---

## 6. Where everything lives

| Thing | Where |
| --- | --- |
| The Raspberry Pi | `leaps-rpi-1`, campus network, address `10.203.49.199`, login user `leaps-admin` |
| The code + data on the Pi | `/home/leaps-admin/az-power-outage-archive` |
| The code + data online | <https://github.com/vmanam1/az-power-outage-archive> |
| The dashboard | <http://10.203.49.199:5000> (campus network only) |
| Data files | `data/<utility>/<date>_<time>.json` — one file per utility per hour |
| Monitoring | healthchecks.io, check name `az-outage-pi`, alerts to vmanam1@asu.edu |
| Collector schedule | systemd timer `outage-archive.timer`, fires hourly at :07 |
| Dashboard service | systemd service `outage-dashboard.service`, port 5000 |
| Secrets (never in GitHub) | deploy key at `~/.ssh/id_ed25519_ghdeploy` on the Pi; healthchecks URL in `/etc/default/outage-archive` on the Pi |

---

## 7. Operations manual (commands included)

> These require connecting to the Pi over **SSH** (a secure remote terminal). From any computer on the campus network, open a terminal and run: `ssh leaps-admin@10.203.49.199` — you'll need the account password or an authorized SSH key.

### Check status of both services
```bash
systemctl status outage-archive.timer      # the hourly collection alarm clock
systemctl status outage-dashboard.service  # the dashboard website
systemctl list-timers outage-archive.timer # shows when the next run fires
```

### See what the last collection run did
```bash
journalctl -u outage-archive.service -n 50   # last 50 log lines
```
A healthy run logs one "quality check passed" line per utility and ends with a commit + push.

### Trigger a collection run right now (instead of waiting for :07)
```bash
sudo systemctl start outage-archive.service
```

### Restart the dashboard
```bash
sudo systemctl restart outage-dashboard.service
```

### Deploy a code change (developer workflow)
1. Make changes on your own computer, commit, and `git push` to GitHub (`main` branch). Tests run automatically on GitHub — check they're green.
2. On the Pi: `cd ~/az-power-outage-archive && git pull`
3. If you changed `app.py` or anything in `templates/`: `sudo systemctl restart outage-dashboard.service`. Changes to JS/CSS in `static/` or to the providers need **no** restart.

### Run the test suite
```bash
cd ~/az-power-outage-archive && ./venv/bin/python -m unittest discover -s tests
```
(On Windows: `python -m unittest discover -s tests` inside the project folder.)

---

## 8. Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| Email from healthchecks.io ("check is down") | Pi is off, lost network, disk full, or push credentials broke | Check the Pi has power/network; SSH in and run `journalctl -u outage-archive.service -n 100` to read the error |
| No hourly commits on GitHub, but no email either | GitHub itself may be down, or check the healthchecks.io site | Wait one cycle; then SSH in and inspect logs as above |
| `systemctl status outage-archive.service` shows "failed" but commits keep appearing | One utility's website is down; the other eight still archived | Nothing — this is by design and self-recovers when the utility comes back |
| Dashboard won't load | You're not on the campus network — the Pi is not reachable from home | Connect from campus (or set up Tailscale — see "Future ideas") |
| Dashboard loads but looks broken after an update | Browser cached old files (rare since July 27 fix) | Hard refresh: **Ctrl+Shift+R** |
| A red "Query Error / Display Error" toast on the dashboard | The toast now includes the real error message | Screenshot it — the message pinpoints the cause |
| Pi rebooted (power cut) | — | Nothing. Both services start on boot; a missed run is made up automatically |
| Need to re-run collection in the cloud (Pi long-term dead) | — | GitHub → Actions → "Archive Arizona Power Outages" → Run workflow (manual). To restore hourly cloud runs, un-comment the `schedule:` block in `.github/workflows/scrape.yml` |

---

## 9. Understanding the data files

Each hourly snapshot is a small JSON file, e.g. `data/aps/2026-07-27_11-07.json`:

```json
{
  "metadata": { "provider": "APS", "scraped_at": "2026-07-27 11:07:35 MST", "source": "APS ArcGIS REST API" },
  "summary":  { "outage_count": 2, "customers_affected": 447 },
  "outages": [
    { "latitude": 33.45, "longitude": -111.95, "customers": 42,
      "cause": "Equipment Failure", "start_time": "2026-07-27 09:31:00 MST",
      "etr": "2026-07-27 14:00:00 MST" }
  ]
}
```

- All times are **Arizona time (MST)** — Arizona doesn't observe daylight saving.
- Files store **only what the utility published**. The "≈ region" names on the dashboard are computed on the fly and never written into the files.
- A customer count of 0 can mean "genuinely zero" or "utility didn't say" — treat with care.

---

## 10. Glossary (for non-technical readers)

| Term | Meaning |
| --- | --- |
| **Raspberry Pi** | A credit-card-sized, low-power computer. Ours runs Linux and works 24/7. |
| **GitHub / repository ("repo")** | A website that stores code and files with full history of every change. Our repo is the online copy of everything. |
| **Commit** | One saved change in the repository's history — like a snapshot with a note. |
| **Push / pull** | Uploading your commits to GitHub / downloading the latest ones from it. |
| **JSON** | A simple text format for structured data — what the utilities publish and what we archive. |
| **API** | A way for programs to ask a website for data directly, instead of reading the human page. |
| **Scraper / collector / provider** | Our small programs that fetch each utility's data. |
| **systemd / service / timer** | Linux's manager for background programs. A *service* is a program it keeps running; a *timer* is an alarm clock that starts one on schedule. |
| **SSH** | A secure way to type commands on another computer over the network. |
| **Deploy key** | A machine-only credential that lets the Pi upload to exactly one GitHub repository. |
| **Dead-man's-switch** | Monitoring that alarms when a regular "I'm alive" signal *stops* — instead of trying to detect every possible failure. |
| **Flask** | The small Python web framework that powers the dashboard. |
| **venv** | A private folder of Python packages for this project, so it doesn't disturb the rest of the system. |
| **ETR** | Estimated Time of Restoration — the utility's guess for when power returns. |
| **MST** | Mountain Standard Time (UTC−7) — Arizona's year-round time. |

---

## 11. Future ideas (optional, not gaps)

- **Tailscale** — a free private network so the dashboard can be viewed off-campus without exposing it to the internet.
- **SSVEC large-outage polygons** — SSVEC publishes outage *area shapes* during major events only; could be archived when one occurs.
- **Repo housekeeping** — at ~79k files/year the archive will eventually warrant a retention or packing strategy (years away).

---

## 12. Quick reference card

```
Dashboard ........... http://10.203.49.199:5000        (campus network)
GitHub .............. github.com/vmanam1/az-power-outage-archive
Pi login ............ ssh leaps-admin@10.203.49.199
Project folder ...... ~/az-power-outage-archive
Collection runs ..... hourly at :07 (systemd timer)
Manual run .......... sudo systemctl start outage-archive.service
Restart dashboard ... sudo systemctl restart outage-dashboard.service
Logs ................ journalctl -u outage-archive.service -n 50
Alerts .............. healthchecks.io -> vmanam1@asu.edu (email = problem)
```
