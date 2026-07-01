import requests

from providers.base import BaseProvider
from scripts.config import APS_URL, APS_PARAMS, REQUEST_TIMEOUT
from scripts.utils import format_epoch, current_time


class APSProvider(BaseProvider):

    def __init__(self):
        super().__init__("aps")

    def fetch_data(self):
        try:
            response = requests.get(
                APS_URL,
                params=APS_PARAMS,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            features = response.json().get("features", [])

            outages = []
            customers_affected = 0

            for feature in features:

                attr = feature.get("attributes", {})

                customers = attr.get("customers") or 0
                customers_affected += customers

                outages.append({
                    "city": attr.get("City"),
                    "boundary": attr.get("Boundary"),
                    "customers": customers,
                    "cause": attr.get("Cause"),
                    "start_time": format_epoch(attr.get("off")),
                    "etr": format_epoch(attr.get("etr"))
                })

            return {
                "metadata": {
                    "provider": "APS",
                    "scraped_at": current_time(),
                    "source": "APS ArcGIS REST API",
                    "scraper_version": "1.0.0"
                },
                "summary": {
                    "outage_count": len(outages),
                    "customers_affected": customers_affected
                },
                "outages": outages
            }
    
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch APS data: {e}")