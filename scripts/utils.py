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
