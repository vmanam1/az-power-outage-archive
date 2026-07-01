from datetime import datetime, timezone
import hashlib
import json

def format_epoch(epoch_ms):
    """
    Convert ArcGIS epoch milliseconds to
    YYYY-MM-DD HH:MM:SS UTC
    """

    if not epoch_ms:
        return None

    return datetime.fromtimestamp(
        epoch_ms / 1000,
        tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M:%S UTC")


def current_time():
    """
    Returns the current UTC time.
    """

    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

def calculate_hash(data: dict) -> str:
    """
    Returns a SHA-256 hash of the JSON data.
    """

    json_string = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        json_string.encode("utf-8")
    ).hexdigest()