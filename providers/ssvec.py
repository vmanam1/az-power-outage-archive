import requests

from providers.base import BaseProvider
from scripts.config import REQUEST_TIMEOUT, SSVEC_PARAMS, SSVEC_URL
from scripts.http import request_with_retries
from scripts.utils import format_epoch


class SSVECProvider(BaseProvider):
    def __init__(self):
        super().__init__("ssvec")

    def get_source(self):
        return "SSVEC ArcGIS Outage API"

    def fetch_data(self):
        try:
            response = request_with_retries(
                requests.get,
                SSVEC_URL,
                params=SSVEC_PARAMS,
                timeout=REQUEST_TIMEOUT,
            )
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"Failed to fetch SSVEC data: {exc}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("SSVEC response must be an object")
        if payload.get("error"):
            raise RuntimeError(f"SSVEC API returned an error: {payload['error']}")
        if not isinstance(payload.get("features"), list):
            raise RuntimeError("SSVEC response is missing a features list")

        return self.parse_data(payload)

    def parse_data(self, payload):
        outages = []
        customers_affected = 0

        for feature in payload["features"]:
            if not isinstance(feature, dict):
                raise ValueError("SSVEC feature must be an object")
            attributes = feature.get("attributes") or {}
            geometry = feature.get("geometry") or {}
            if not isinstance(attributes, dict) or not isinstance(geometry, dict):
                raise ValueError(
                    "SSVEC feature has malformed attributes or geometry"
                )
            customers = self.parse_customer_count(
                attributes.get("CUSTOMER_COUNT"), "CUSTOMER_COUNT"
            )
            customers_affected += customers

            outages.append({
                "incident_id": attributes.get("INCIDENT_ID"),
                "latitude": geometry.get("y"),
                "longitude": geometry.get("x"),
                "city": attributes.get("REGION"),
                "customers": customers,
                "cause": attributes.get("CAUSE"),
                "comments": attributes.get("STATUS"),
                "start_time": format_epoch(attributes.get("TIME_OUTAGE")),
                "etr": format_epoch(attributes.get("TIME_RESTORED_EST")),
                "restored_time": format_epoch(attributes.get("TIME_RESTORED")),
            })

        return self.validate_snapshot({
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(outages),
                "customers_affected": customers_affected,
            },
            "outages": outages,
        })
