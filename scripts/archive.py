import json
from pathlib import Path
from datetime import datetime

from scripts.utils import ARIZONA_TZ, snapshot_content_hash

DATA_FOLDER = Path("data")


def _snapshot_filename(data: dict) -> str:
    """
    Derive the snapshot filename from ``metadata.scraped_at`` so the filename
    and the recorded scrape time always agree. Falls back to the current
    Arizona time if the timestamp is missing or unparseable.
    """
    scraped_at = (data.get("metadata") or {}).get("scraped_at")
    if isinstance(scraped_at, str):
        try:
            dt = datetime.strptime(scraped_at, "%Y-%m-%d %H:%M:%S MST")
            return dt.strftime("%Y-%m-%d_%H-%M.json")
        except ValueError:
            pass
    return datetime.now(ARIZONA_TZ).strftime("%Y-%m-%d_%H-%M.json")


def get_latest_snapshot(provider_name: str):

    provider_folder = DATA_FOLDER / provider_name

    if not provider_folder.exists():
        return None

    json_files = sorted(provider_folder.glob("*.json"))

    if not json_files:
        return None

    return json_files[-1]


def save_snapshot(provider_name: str, data: dict):

    provider_folder = DATA_FOLDER / provider_name
    provider_folder.mkdir(parents=True, exist_ok=True)

    latest = get_latest_snapshot(provider_name)

    if latest:

        with open(latest, "r", encoding="utf-8") as f:
            old_data = json.load(f)

        if snapshot_content_hash(old_data) == snapshot_content_hash(data):
            return False, latest

    filename = _snapshot_filename(data)

    filepath = provider_folder / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

    return True, filepath
