import math
from datetime import datetime
from xml.etree import ElementTree

import requests

from providers.base import BaseProvider
from scripts.config import REQUEST_TIMEOUT
from scripts.utils import ARIZONA_TZ


class ED3Provider(BaseProvider):
    API_URL = "https://ww3.ed3online.org/OMSWebMap/MobileMap/OMSMobileService.asmx/GetAllOutages"

    def __init__(self):
        super().__init__("ed3")

    def get_source(self):
        return "ED3 OMS Mobile Outage Service"

    def fetch_data(self):
        try:
            response = requests.get(self.API_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (requests.RequestException, ElementTree.ParseError) as exc:
            raise RuntimeError(f"Failed to fetch ED3 data: {exc}") from exc

        return self.parse_xml(root)

    def parse_xml(self, root):
        outages = []
        customers_affected = 0

        for outage in self._children(root, "MobileOutage"):
            customers = self._to_int(self._text(outage, "CutomersAffected"))
            customers_affected += customers
            latitude, longitude = self._coordinates(
                self._to_float(self._text(outage, "X")),
                self._to_float(self._text(outage, "Y")),
            )
            outages.append({
                "latitude": latitude,
                "longitude": longitude,
                "boundary": self._text(outage, "ElementName"),
                "customers": customers,
                "cause": self._text(outage, "Cause"),
                "comments": self._text(outage, "CaseStatus"),
                "start_time": self.format_time(self._text(outage, "OutageTime")),
                "etr": self.format_time(self._text(outage, "RestorationTime")),
                "pole_number": self._text(outage, "PoleNumber"),
            })

        return {
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(outages),
                "customers_affected": customers_affected,
                "total_customers": self._to_int(self._text(root, "TotalCustomers")),
            },
            "outages": outages,
        }

    @staticmethod
    def _children(root, name):
        return [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == name]

    @classmethod
    def _text(cls, root, name):
        elements = cls._children(root, name)
        if not elements or not elements[0].text:
            return None
        return elements[0].text.strip() or None

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
    def _coordinates(x, y):
        if x is None or y is None:
            return None, None
        if abs(x) <= 180 and abs(y) <= 90:
            return y, x
        longitude = x * 180 / 20037508.34
        latitude = math.degrees(
            2 * math.atan(math.exp(math.radians(y * 180 / 20037508.34)))
            - math.pi / 2
        )
        return latitude, longitude

    @staticmethod
    def format_time(value):
        if not value:
            return None
        for date_format in (
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %I:%M %p",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return datetime.strptime(value, date_format).replace(
                    tzinfo=ARIZONA_TZ
                ).strftime("%Y-%m-%d %H:%M:%S %Z")
            except ValueError:
                continue
        return None
