import requests
from datetime import datetime

from providers.base import BaseProvider
from scripts.utils import ARIZONA_TZ


class SRPProvider(BaseProvider):

    API_URL = "https://myaccount.srpnet.com/myaccountapi/api/outages/getall"

    def __init__(self):
        super().__init__("srp")

    def get_source(self):
        return "SRP Outage API"

    def fetch_data(self):

        response = requests.get(self.API_URL, timeout=30)
        response.raise_for_status()

        outages = response.json()

        formatted = []

        total_customers = 0

        for outage in outages:

            customers = outage.get("numberCustomersAffected", 0)
            total_customers += customers

            formatted.append({
                "latitude": outage.get("latitude"),
                "longitude": outage.get("longitude"),
                "boundary": outage.get("crossRoadText"),
                "customers": customers,
                "cause": outage.get("outageProblem"),
                "start_time": self.format_time(
                    outage.get("outageBegan")
                ),
                "etr": self.format_time(
                    outage.get("estimatedRestorationTime")
                )
            })

        return {
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(formatted),
                "customers_affected": total_customers
            },
            "outages": formatted
        }

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
