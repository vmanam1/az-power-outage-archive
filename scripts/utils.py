from datetime import datetime, timedelta, timezone
import hashlib
import json


ARIZONA_TZ = timezone(timedelta(hours=-7), name="MST")

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
