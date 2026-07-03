import requests
from datetime import datetime

from providers.base import BaseProvider
from scripts.config import REQUEST_TIMEOUT
from scripts.http import request_with_retries
from scripts.utils import ARIZONA_TZ


CAUSE_SUMMARIES = {
    "An SRP maintenance crew is performing critical maintenance work to repair or upgrade equipment. Power will be restored as quickly as possible.": "Critical equipment maintenance",
    "An underground power cable has failed. SRP crews are working to restore power.": "Underground cable failure",
    "We are investigating the cause of the outage.": "Cause under investigation",
    "Electrical equipment has been hit or damaged. SRP crews are working to restore power.": "Electrical equipment damage",
    "Excavation equipment caused damage to underground power lines. SRP crews are working to restore power.": "Excavation damaged underground lines",
    "Public safety power shutoff due to wildfire mitigation in the area.": "Wildfire safety power shutoff",
    "Power lines are down in the area. SRP crews are working to restore power.": "Downed power lines",
}


def summarize_cause(comments):
    if not comments:
        return None

    return CAUSE_SUMMARIES.get(comments, "Other outage cause")


class SRPProvider(BaseProvider):

    API_URL = "https://myaccount.srpnet.com/myaccountapi/api/outages/getall"

    def __init__(self):
        super().__init__("srp")

    def get_source(self):
        return "SRP Outage API"

    def fetch_data(self):
        try:
            response = request_with_retries(
                requests.get,
                self.API_URL,
                timeout=REQUEST_TIMEOUT,
            )
            outages = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"Failed to fetch SRP data: {exc}") from exc

        if not isinstance(outages, list):
            raise RuntimeError("Failed to fetch SRP data: response must be a list")

        formatted = []

        total_customers = 0

        for outage in outages:
            if not isinstance(outage, dict):
                raise RuntimeError("Failed to fetch SRP data: outage must be an object")

            try:
                customers = self.parse_customer_count(
                    outage.get("numberCustomersAffected"),
                    "numberCustomersAffected",
                )
            except ValueError as exc:
                raise RuntimeError(f"Failed to fetch SRP data: {exc}") from exc
            comments = outage.get("outageProblem")
            total_customers += customers

            formatted.append({
                "latitude": outage.get("latitude"),
                "longitude": outage.get("longitude"),
                "boundary": outage.get("crossRoadText"),
                "customers": customers,
                "cause": summarize_cause(comments),
                "comments": comments,
                "start_time": self.format_time(
                    outage.get("outageBegan")
                ),
                "etr": self.format_time(
                    outage.get("estimatedRestorationTime")
                )
            })

        return self.validate_snapshot({
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(formatted),
                "customers_affected": total_customers
            },
            "outages": formatted
        })

    @staticmethod
    def format_time(value):

        if not value:
            return None

        return (
            datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
            .astimezone(ARIZONA_TZ)
            .strftime("%Y-%m-%d %H:%M %Z")
        )
