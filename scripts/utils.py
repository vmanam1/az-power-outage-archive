from datetime import datetime, timedelta, timezone
import hashlib
import json


ARIZONA_TZ = timezone(timedelta(hours=-7), name="MST")

# Arizona's borders are almost exactly a lat/lon rectangle, so a bounding box
# is enough to keep this an Arizona-only archive. Its real job is the eastern
# edge (some tracked utilities, e.g. Navopache, also serve New Mexico) and the
# southern edge (Mexico); the west/north edges are generous, which is harmless
# because the tracked utilities' territories end well inside them.
ARIZONA_BOUNDS = {
    "min_latitude": 31.325,     # Mexico border
    "max_latitude": 37.005,     # Utah border
    "min_longitude": -114.82,   # California/Nevada border
    "max_longitude": -109.045,  # New Mexico border
}


def is_in_arizona(latitude, longitude):
    """True when the coordinates fall inside Arizona's bounding box."""
    if not isinstance(latitude, (int, float)) or isinstance(latitude, bool):
        return False
    if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
        return False
    return (
        ARIZONA_BOUNDS["min_latitude"] <= latitude <= ARIZONA_BOUNDS["max_latitude"]
        and ARIZONA_BOUNDS["min_longitude"] <= longitude <= ARIZONA_BOUNDS["max_longitude"]
    )


def filter_snapshot_to_arizona(data):
    """
    Drops outages whose coordinates fall outside Arizona and recomputes the
    summary counts. Records without coordinates are kept -- they cannot be
    judged, and validation guarantees they carry another identifier.

    Returns ``(data, dropped_count, dropped_customers)``; when nothing is
    dropped the original object is returned untouched.
    """
    outages = data.get("outages")
    if not isinstance(outages, list):
        return data, 0, 0

    kept, dropped_count, dropped_customers = [], 0, 0
    for outage in outages:
        latitude = outage.get("latitude") if isinstance(outage, dict) else None
        longitude = outage.get("longitude") if isinstance(outage, dict) else None
        if latitude is not None and longitude is not None and not is_in_arizona(
            latitude, longitude
        ):
            dropped_count += 1
            customers = outage.get("customers")
            if isinstance(customers, int) and not isinstance(customers, bool):
                dropped_customers += customers
            continue
        kept.append(outage)

    if dropped_count == 0:
        return data, 0, 0

    filtered = dict(data)
    filtered["outages"] = kept
    summary = dict(data.get("summary") or {})
    summary["outage_count"] = len(kept)
    if isinstance(summary.get("customers_affected"), int):
        summary["customers_affected"] = max(
            0, summary["customers_affected"] - dropped_customers
        )
    filtered["summary"] = summary
    return filtered, dropped_count, dropped_customers

def format_epoch(epoch_ms):
    """
    Convert ArcGIS epoch milliseconds to Arizona time.
    """

    if not epoch_ms:
        return None

    return datetime.fromtimestamp(
        epoch_ms / 1000,
        tz=timezone.utc
    ).astimezone(ARIZONA_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


def current_time():
    """
    Returns the current Arizona time.
    """

    return datetime.now(ARIZONA_TZ).strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )

def calculate_hash(data) -> str:
    """
    Returns a SHA-256 hash of any JSON-serializable value.
    """

    json_string = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        json_string.encode("utf-8")
    ).hexdigest()


def snapshot_content_hash(data: dict) -> str:
    """
    Returns a hash of the parts of a snapshot that represent a real change.

    Only the outage payload is hashed. Volatile metadata such as
    ``metadata.scraped_at`` (a fresh wall-clock timestamp every run) and feed
    refresh markers like ``summary.map_last_refreshed`` are intentionally
    excluded, so two scrapes with identical outages are recognised as
    unchanged and are not re-archived. ``summary`` counts are derived from the
    outages, so hashing the outages alone is sufficient.
    """

    return calculate_hash(data.get("outages") or [])
