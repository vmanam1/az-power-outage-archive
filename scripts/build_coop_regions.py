"""
Regenerates dashboard/coop_regions.json: the named region polygons of every
NISC hosted-outage-map co-op, keyed by provider name.

The dashboard uses this file to backfill a display-only "boundary" for co-op
records that were archived without one (snapshots from before the collector
learned region lookup). Rings are stored fully decoded in absolute Web
Mercator meters, ready for point-in-polygon tests.

Run from the repo root whenever a co-op redraws its regions:

    python -m scripts.build_coop_regions
"""

import json
import os

from providers.dixie import DixieProvider
from providers.garkane import GarkaneProvider
from providers.mohave import MohaveProvider
from providers.navopache import NavopacheProvider
from providers.trico import TricoProvider

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "dashboard", "coop_regions.json")


def main():
    result = {}
    for provider in (
        MohaveProvider(), TricoProvider(), NavopacheProvider(),
        DixieProvider(), GarkaneProvider(),
    ):
        config = provider._fetch_json("config.json")
        regions = provider._load_regions(config)
        result[provider.name] = [
            {"name": name, "rings": [[list(pt) for pt in ring] for ring in rings]}
            for name, rings in regions
        ]
        print(f"{provider.name}: {len(regions)} regions")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, separators=(",", ":"))
    print(f"wrote {OUTPUT} ({os.path.getsize(OUTPUT)} bytes)")


if __name__ == "__main__":
    main()
