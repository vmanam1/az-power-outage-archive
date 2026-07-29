import os
import json
import logging
import threading
import time
from datetime import datetime
from dashboard.cache import global_cache
from dashboard.normalizer import normalize_outage, normalize_time
from scripts.utils import ARIZONA_TZ, is_in_arizona

logger = logging.getLogger("outage_dashboard")

# Cache of the fully assembled (snapshots, stats) result per data directory,
# keyed by a cheap directory fingerprint. A single dashboard page load hits
# /api/metadata, /api/outages and /api/timeline, each of which previously
# rebuilt the entire snapshot list; caching the assembled result lets those
# requests share one scan until the archive actually changes.
_scan_cache = {}
_scan_cache_lock = threading.Lock()

class DataQualityStats:
    def __init__(self):
        self.malformed_files = 0
        self.missing_coords = 0
        self.invalid_coords = 0
        # Records archived before the Arizona-only collector filter existed
        # (e.g. Navopache's New Mexico territory) are hidden at read time.
        self.out_of_state = 0
        self.total_snapshots = 0

# The fingerprint is consulted on every API request (a page load fires four
# at once), and the archive gains ~200 files a day forever. Two mitigations
# keep it cheap as the tree grows: os.scandir with DirEntry.stat() (far fewer
# syscalls than os.walk + per-path getmtime), and a short TTL memo that
# collapses same-page-load bursts into one sweep. The memo means a brand-new
# change can take up to _FINGERPRINT_TTL_SECONDS to be noticed -- irrelevant
# at the frontend's 60s polling cadence; tests that need exact immediacy set
# the TTL to 0.
_FINGERPRINT_TTL_SECONDS = 2.0
_fingerprint_cache = {}
_fingerprint_lock = threading.Lock()


def _compute_fingerprint(data_dir):
    file_count = 0
    max_mtime = 0.0
    if not os.path.exists(data_dir):
        return file_count, max_mtime

    try:
        with os.scandir(data_dir) as top:
            provider_dirs = [e.path for e in top if e.is_dir() and not e.name.startswith(".")]
    except OSError:
        return file_count, max_mtime

    for provider_dir in provider_dirs:
        try:
            with os.scandir(provider_dir) as inner:
                for f in inner:
                    if not f.name.endswith(".json"):
                        continue
                    file_count += 1
                    try:
                        mtime = f.stat().st_mtime
                        if mtime > max_mtime:
                            max_mtime = mtime
                    except OSError:
                        pass
        except OSError:
            continue

    return file_count, max_mtime


def archive_fingerprint(data_dir="data"):
    """
    Returns a cheap (json_file_count, max_mtime) fingerprint of the archive.
    Changing snapshots (added, removed, or modified) changes the fingerprint,
    which is used both to invalidate the scan cache and to power the
    frontend's lightweight update polling.
    """
    now = time.monotonic()
    with _fingerprint_lock:
        cached = _fingerprint_cache.get(data_dir)
        if cached and now - cached[0] < _FINGERPRINT_TTL_SECONDS:
            return cached[1]

    result = _compute_fingerprint(data_dir)
    with _fingerprint_lock:
        _fingerprint_cache[data_dir] = (now, result)
    return result

def parse_filename_time(filename):
    """
    Attempts to extract MST date/time from standard outage filenames
    like '2026-07-15_16-07.json'.
    """
    base = os.path.basename(filename)
    # Remove extension
    name, _ = os.path.splitext(base)
    try:
        dt = datetime.strptime(name, "%Y-%m-%d_%H-%M")
        return dt.strftime("%Y-%m-%d %H:%M:%S MST")
    except ValueError:
        return None

def parse_snapshot_file(file_path, provider_name, stats):
    """
    Parses a single JSON snapshot file, tracking and caching coordinates & data quality stats.
    """
    cached = global_cache.get(file_path)
    if cached is not None:
        if cached.get("error"):
            stats.malformed_files += 1
            return None
        stats.missing_coords += cached["stats"]["missing_coords"]
        stats.invalid_coords += cached["stats"]["invalid_coords"]
        stats.out_of_state += cached["stats"].get("out_of_state", 0)
        return cached

    # Parse and extract
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Malformed or unreadable JSON file skipped: {file_path}. Error: {e}")
        stats.malformed_files += 1
        global_cache.set(file_path, {"error": True})
        return None

    if not isinstance(data, dict):
        logger.warning(f"JSON root in {file_path} is not an object. Skipped.")
        stats.malformed_files += 1
        global_cache.set(file_path, {"error": True})
        return None

    metadata = data.get("metadata") or {}
    scraped_at = None
    if isinstance(metadata, dict):
        scraped_at = metadata.get("scraped_at")

    scraped_at = normalize_time(scraped_at)
    if not scraped_at:
        scraped_at = parse_filename_time(file_path)

    if not scraped_at:
        try:
            mtime = os.path.getmtime(file_path)
            dt = datetime.fromtimestamp(mtime, tz=ARIZONA_TZ)
            scraped_at = dt.strftime("%Y-%m-%d %H:%M:%S MST")
        except OSError:
            scraped_at = datetime.now(ARIZONA_TZ).strftime("%Y-%m-%d %H:%M:%S MST")

    raw_outages = data.get("outages")
    if not isinstance(raw_outages, list):
        raw_outages = []

    normalized_outages = []
    file_missing_coords = 0
    file_invalid_coords = 0
    file_out_of_state = 0

    for out in raw_outages:
        if not isinstance(out, dict):
            continue
        orig_lat = out.get("latitude")
        orig_lng = out.get("longitude")

        norm = normalize_outage(out, provider_name)

        # This is an Arizona-only archive: hide records outside the state
        # (older snapshots predate the collector-side filter). Records
        # without coordinates cannot be judged and are kept.
        norm_lat = norm.get("latitude")
        norm_lng = norm.get("longitude")
        if norm_lat is not None and norm_lng is not None and not is_in_arizona(
            norm_lat, norm_lng
        ):
            file_out_of_state += 1
            continue

        normalized_outages.append(norm)

        # Coordinate evaluation
        if orig_lat is None or orig_lng is None:
            file_missing_coords += 1
        else:
            if norm.get("latitude") is None:
                file_invalid_coords += 1

    stats.missing_coords += file_missing_coords
    stats.invalid_coords += file_invalid_coords
    stats.out_of_state += file_out_of_state

    summary = data.get("summary") or {}
    customers_affected = summary.get("customers_affected")
    if customers_affected is None or file_out_of_state:
        # Stored totals include the hidden records; recompute from the kept.
        customers_affected = sum(o["customers"] for o in normalized_outages)

    # Total customers served (only some utilities publish it).
    total_customers = summary.get("total_customers")
    if (
        isinstance(total_customers, bool)
        or not isinstance(total_customers, int)
        or total_customers <= 0
    ):
        total_customers = None

    snapshot = {
        "file_path": file_path,
        "provider": provider_name.lower(),
        "scraped_at": scraped_at,
        "outages": normalized_outages,
        "customers_affected": customers_affected,
        "total_customers": total_customers,
        "stats": {
            "missing_coords": file_missing_coords,
            "invalid_coords": file_invalid_coords,
            "out_of_state": file_out_of_state
        }
    }

    global_cache.set(file_path, snapshot)
    return snapshot

def scan_archive(data_dir="data"):
    """
    Crawls data_dir dynamically, parsing all providers and snapshots.

    The assembled result is cached per directory and reused until the archive
    fingerprint changes, so repeated calls within a request cycle are cheap.
    """
    fingerprint = archive_fingerprint(data_dir)
    with _scan_cache_lock:
        entry = _scan_cache.get(data_dir)
        if entry is not None and entry["fingerprint"] == fingerprint:
            return entry["result"]

    stats = DataQualityStats()
    snapshots = []

    if not os.path.exists(data_dir):
        logger.warning(f"Data directory {data_dir} does not exist.")
        return snapshots, stats

    providers = []
    try:
        items = os.listdir(data_dir)
    except OSError as e:
        logger.error(f"Failed to read data directory {data_dir}: {e}")
        return snapshots, stats

    for item in items:
        full_path = os.path.join(data_dir, item)
        if os.path.isdir(full_path) and not item.startswith("."):
            providers.append(item.lower())

    for provider in providers:
        provider_path = os.path.join(data_dir, provider)
        try:
            filenames = os.listdir(provider_path)
        except OSError:
            continue
        for filename in filenames:
            if filename.endswith(".json"):
                file_path = os.path.join(provider_path, filename)
                stats.total_snapshots += 1
                snap = parse_snapshot_file(file_path, provider, stats)
                if snap:
                    snapshots.append(snap)

    result = (snapshots, stats)
    with _scan_cache_lock:
        _scan_cache[data_dir] = {"fingerprint": fingerprint, "result": result}
    return result
