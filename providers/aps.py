import requests

from providers.base import BaseProvider
from scripts.config import APS_URL, APS_PARAMS, REQUEST_TIMEOUT
from scripts.http import request_with_retries
from scripts.utils import format_epoch


class APSProvider(BaseProvider):

    def __init__(self):
        super().__init__("aps")

    def get_source(self):
        return "APS ArcGIS REST API"

    def fetch_data(self):
        try:
            response = request_with_retries(
                requests.get,
                APS_URL,
                params=APS_PARAMS,
                timeout=REQUEST_TIMEOUT
            )

            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                raise ValueError(f"APS API returned an error: {payload['error']}")
            if not isinstance(payload, dict) or not isinstance(
                payload.get("features"), list
            ):
                raise ValueError("APS response is missing a features list")

            features = payload["features"]

            outages = []
            customers_affected = 0

            for feature in features:

                if not isinstance(feature, dict):
                    raise ValueError("APS feature must be an object")
                attr = feature.get("attributes")
                geometry = feature.get("geometry")

                if not isinstance(attr, dict) or not isinstance(geometry, dict):
                    raise ValueError("APS feature has malformed attributes or geometry")

                customers = self.parse_customer_count(
                    attr.get("customers"), "customers"
                )
                customers_affected += customers

                outages.append({
                    "latitude": geometry.get("y"),
                    "longitude": geometry.get("x"),
                    "city": attr.get("City"),
                    "boundary": attr.get("Boundary"),
                    "customers": customers,
                    "cause": attr.get("Cause"),
                    "comments": attr.get("Comments"),
                    "start_time": format_epoch(attr.get("off")),
                    "etr": format_epoch(attr.get("etr"))
                })

            return self.validate_snapshot({
                "metadata": self.build_metadata(),
                "summary": {
                    "outage_count": len(outages),
                    "customers_affected": customers_affected
                },
                "outages": outages
            })
    
        except (requests.RequestException, ValueError, TypeError) as e:
            raise RuntimeError(f"Failed to fetch APS data: {e}")
