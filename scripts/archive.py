import json
from pathlib import Path
from datetime import datetime, timezone

from scripts.utils import calculate_hash

DATA_FOLDER = Path("data")


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

        if calculate_hash(old_data) == calculate_hash(data):
            return False, latest

    filename = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d_%H-%M.json")

    filepath = provider_folder / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

    return True, filepath