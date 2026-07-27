import math

import requests

from providers.base import BaseProvider
from scripts.config import REQUEST_TIMEOUT
from scripts.http import request_with_retries
from scripts.utils import format_epoch


class CoopOutageMapProvider(BaseProvider):
    """
    Reader for NISC's hosted outage map (outagemap.coop).

    The public map at https://<utility>.outagemap.coop is an SPA that reads
    static JSON from https://outagemap-data.cloud.coop/<slug>/Hosted_Outage_Map/.
    summary.json carries the outage list (real customer counts, cause, crew
    comments, planned flag, and sometimes an ETR) and config.json carries the
    map's boundaryExtent in Web Mercator meters. Each outage's x/y is an
    offset in meters from that extent's south-west corner, so coordinates are
    recovered with an inverse Mercator projection -- verified to match the
    utilities' own map markers exactly.

    This replaces driving the legacy ebill NISC map with headless Chrome: the
    JSON is faster, far more reliable, and richer than the popup cards.
    """

    SLUG = None
    DATA_BASE = "https://outagemap-data.cloud.coop"

    def get_source(self):
        return f"{self.name.upper()} NISC Hosted Outage Map (outagemap.coop)"

    def _fetch_json(self, filename):
        url = f"{self.DATA_BASE}/{self.SLUG}/Hosted_Outage_Map/{filename}"
        response = request_with_retries(
            requests.get,
            url,
            timeout=REQUEST_TIMEOUT
        )
        return response.json()

    @staticmethod
    def _web_mercator_to_wgs84(x, y):
        longitude = x / 20037508.34 * 180
        latitude = math.degrees(
            2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2
        )
        return latitude, longitude

    @staticmethod
    def _clean_text(value):
        if isinstance(value, str):
            return value.strip() or None
        return None

    def fetch_data(self):
        try:
            config = self._fetch_json("config.json")
            summary = self._fetch_json("summary.json")

            extent = (config.get("mapSettings") or {}).get("boundaryExtent")
            if (
                not isinstance(extent, list)
                or len(extent) != 4
                or not all(isinstance(v, (int, float)) for v in extent)
            ):
                raise ValueError("config.json has no usable boundaryExtent")
            xmin, ymin = extent[0], extent[1]

            raw_outages = summary.get("outages")
            if raw_outages is None:
                raw_outages = []
            if not isinstance(raw_outages, list):
                raise ValueError("summary.json outages is not a list")

            outages = []
            customers_affected = 0

            for raw in raw_outages:
                if not isinstance(raw, dict):
                    raise ValueError("summary.json outage must be an object")

                customers = self.parse_customer_count(
                    raw.get("nbrOut"), "nbrOut"
                )
                customers_affected += customers

                x = raw.get("x")
                y = raw.get("y")
                latitude = longitude = None
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    latitude, longitude = self._web_mercator_to_wgs84(
                        xmin + x, ymin + y
                    )

                comments = self._clean_text(raw.get("comment"))
                if raw.get("planned") is True:
                    planned_note = "Planned outage"
                    comments = (
                        f"{planned_note}. {comments}" if comments else planned_note
                    )

                outage_id = raw.get("id")

                outages.append({
                    "latitude": latitude,
                    "longitude": longitude,
                    "customers": customers,
                    "cause": self._clean_text(raw.get("cause")),
                    "comments": comments,
                    "start_time": format_epoch(raw.get("timeOff")),
                    "etr": format_epoch(raw.get("estimateTime")),
                    "incident_id": str(outage_id) if outage_id is not None else None
                })

            snapshot_summary = {
                "outage_count": len(outages),
                "customers_affected": customers_affected
            }
            total_served = summary.get("totalServed")
            if (
                isinstance(total_served, int)
                and not isinstance(total_served, bool)
                and total_served >= customers_affected
            ):
                snapshot_summary["total_customers"] = total_served

            return self.validate_snapshot({
                "metadata": self.build_metadata(),
                "summary": snapshot_summary,
                "outages": outages
            })

        except (requests.RequestException, ValueError, TypeError, KeyError) as e:
            raise RuntimeError(
                f"Failed to fetch {self.name.upper()} outage data: {e}"
            )
