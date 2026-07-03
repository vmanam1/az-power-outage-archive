import requests

from providers.base import BaseProvider
from scripts.config import REQUEST_TIMEOUT, SSVEC_PARAMS, SSVEC_URL
from scripts.utils import format_epoch


class SSVECProvider(BaseProvider):
    def __init__(self):
        super().__init__("ssvec")

    def get_source(self):
        return "SSVEC ArcGIS Outage API"

    def fetch_data(self):
        try:
            response = requests.get(
                SSVEC_URL,
                params=SSVEC_PARAMS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"Failed to fetch SSVEC data: {exc}") from exc

        if payload.get("error"):
            raise RuntimeError(f"SSVEC API returned an error: {payload['error']}")

        return self.parse_data(payload)

    def parse_data(self, payload):
        outages = []
        customers_affected = 0

        for feature in payload.get("features") or []:
            attributes = feature.get("attributes") or {}
            geometry = feature.get("geometry") or {}
            customers = attributes.get("CUSTOMER_COUNT") or 0
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

        return {
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(outages),
                "customers_affected": customers_affected,
            },
            "outages": outages,
        }
