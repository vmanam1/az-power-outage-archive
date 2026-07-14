from datetime import datetime

import requests

from providers.base import BaseProvider
from scripts.config import REQUEST_TIMEOUT
from scripts.utils import ARIZONA_TZ


class TEPProvider(BaseProvider):
    API_URL = "https://apps.tep.com/OutageApp/mapfeed"
    DIVISIONS = frozenset({"TEP"})
    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.tep.com",
        "Referer": "https://www.tep.com/outages/",
        "User-Agent": "az-power-outage-archive/1.0",
    }

    def __init__(self):
        super().__init__("tep")

    def get_source(self):
        return "TEP Outage Map Feed"

    def fetch_data(self):
        try:
            response = requests.post(
                self.API_URL,
                headers=self.HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(
                f"Failed to fetch {self.name.upper()} data: {exc}"
            ) from exc

        return self.parse_data(payload)

    def parse_data(self, payload):
        outages = []
        customers_affected = 0

        for outage in payload.get("outages") or []:
            if outage.get("division") not in self.DIVISIONS:
                continue

            customers = self.parse_customer_count(
                outage.get("customersOut"), "customersOut"
            )
            customers_affected += customers

            cr = outage.get("customersRestored")
            if cr is not None and str(cr).strip() != "":
                try:
                    customers_restored = self.parse_customer_count(cr, "customersRestored")
                except ValueError:
                    customers_restored = 0
            else:
                customers_restored = 0

            outages.append({
                "latitude": self._to_float(outage.get("coordLat")),
                "longitude": self._to_float(outage.get("coordLng")),
                "boundary": outage.get("bounds"),
                "customers": customers,
                "cause": outage.get("updatedCause") or None,
                "comments": outage.get("status") or outage.get("alignMessage") or None,
                "start_time": self.format_time(outage.get("formattedStartTime")),
                "etr": self.format_time(outage.get("formattedEstimatedRestoration")),
                "event": outage.get("event") or None,
                "division": outage.get("division") or None,
                "customers_restored": customers_restored,
                "last_update": self.format_time(
                    outage.get("lastUpdate"),
                    formats=("%m/%d/%Y %I:%M:%S %p",),
                ),
            })

        return {
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(outages),
                "customers_affected": customers_affected,
                "map_last_refreshed": payload.get("mapLastRefreshed"),
            },
            "outages": outages,
        }

    @staticmethod
    def _to_int(value):
        try:
            return int(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def format_time(value, formats=("%b %d, %I:%M %p",), reference=None):
        if not value:
            return None

        reference = reference or datetime.now(ARIZONA_TZ)
        for date_format in formats:
            try:
                if "%Y" not in date_format:
                    temp_value = f"{value} {reference.year}"
                    temp_format = f"{date_format} %Y"
                    parsed = datetime.strptime(temp_value, temp_format)
                    delta = parsed.replace(tzinfo=ARIZONA_TZ) - reference
                    if delta.days > 183:
                        parsed = parsed.replace(year=reference.year - 1)
                    elif delta.days < -183:
                        parsed = parsed.replace(year=reference.year + 1)
                else:
                    parsed = datetime.strptime(value, date_format)
 
                return parsed.replace(tzinfo=ARIZONA_TZ).strftime(
                    "%Y-%m-%d %H:%M %Z"
                )
            except ValueError:
                continue

        return None
