from abc import ABC, abstractmethod
from datetime import datetime
import math
import re

from scripts.utils import current_time


class BaseProvider(ABC):
    def __init__(self, name):
        self.name = name

    def build_metadata(self):
        return {
            "provider": self.name.upper(),
            # A run may inject a shared timestamp (see scripts.run) so every
            # provider in the same hourly cycle records an identical scrape
            # time. Falls back to the current time when run standalone.
            "scraped_at": getattr(self, "scraped_at", None) or current_time(),
            "source": self.get_source(),
            "scraper_version": "1.0.0"
        }

    def get_source(self):
        return "Unknown"

    def validate_snapshot(self, data):
        """Reject malformed snapshots before they are written to the archive."""
        if not isinstance(data, dict):
            raise ValueError(f"{self.name}: snapshot must be an object")

        metadata = data.get("metadata")
        summary = data.get("summary")
        outages = data.get("outages")

        if not isinstance(metadata, dict):
            raise ValueError(f"{self.name}: metadata must be an object")
        if not metadata.get("provider") or not metadata.get("source"):
            raise ValueError(f"{self.name}: metadata is missing provider or source")
        if metadata["provider"] != self.name.upper():
            raise ValueError(f"{self.name}: metadata provider does not match")
        scraped_at = metadata.get("scraped_at")
        if not isinstance(scraped_at, str):
            raise ValueError(f"{self.name}: metadata is missing scraped_at")
        try:
            datetime.strptime(scraped_at, "%Y-%m-%d %H:%M:%S MST")
        except ValueError as exc:
            raise ValueError(
                f"{self.name}: scraped_at must be an MST timestamp"
            ) from exc
        if not isinstance(summary, dict):
            raise ValueError(f"{self.name}: summary must be an object")
        if not isinstance(outages, list):
            raise ValueError(f"{self.name}: outages must be a list")

        outage_count = summary.get("outage_count")
        customers_affected = summary.get("customers_affected")
        if (
            isinstance(outage_count, bool)
            or not isinstance(outage_count, int)
            or outage_count < 0
        ):
            raise ValueError(f"{self.name}: outage_count must be non-negative")
        if (
            isinstance(customers_affected, bool)
            or not isinstance(customers_affected, int)
            or customers_affected < 0
        ):
            raise ValueError(
                f"{self.name}: customers_affected must be non-negative"
            )
        if outage_count != len(outages):
            raise ValueError(f"{self.name}: outage_count does not match outages")
        total_customers = summary.get("total_customers")
        if total_customers is not None and (
            isinstance(total_customers, bool)
            or not isinstance(total_customers, int)
            or total_customers < customers_affected
        ):
            raise ValueError(
                f"{self.name}: total_customers must cover customers_affected"
            )

        calculated_customers = 0
        for index, outage in enumerate(outages):
            if not isinstance(outage, dict):
                raise ValueError(f"{self.name}: outage {index} must be an object")

            customers = outage.get("customers")
            if (
                isinstance(customers, bool)
                or not isinstance(customers, int)
                or customers < 0
            ):
                raise ValueError(
                    f"{self.name}: outage {index} has invalid customers"
                )
            calculated_customers += customers

            latitude = outage.get("latitude")
            longitude = outage.get("longitude")
            if (latitude is None) != (longitude is None):
                raise ValueError(
                    f"{self.name}: outage {index} has incomplete coordinates"
                )
            if latitude is not None and (
                isinstance(latitude, bool)
                or not isinstance(latitude, (int, float))
                or not math.isfinite(latitude)
                or not -90 <= latitude <= 90
            ):
                raise ValueError(
                    f"{self.name}: outage {index} has invalid latitude"
                )
            if longitude is not None and (
                not isinstance(longitude, (int, float))
                or isinstance(longitude, bool)
                or not math.isfinite(longitude)
                or not -180 <= longitude <= 180
            ):
                raise ValueError(
                    f"{self.name}: outage {index} has invalid longitude"
                )

            identity_fields = (
                "incident_id", "city", "boundary", "pole_number"
            )
            if latitude is None and not any(
                outage.get(key) for key in identity_fields
            ):
                raise ValueError(
                    f"{self.name}: outage {index} has no location or identifier"
                )

            for field in ("start_time", "etr", "restored_time"):
                value = outage.get(field)
                if value is None:
                    continue
                if not isinstance(value, str) or not self._is_mst_timestamp(value):
                    raise ValueError(
                        f"{self.name}: outage {index} has invalid {field}"
                    )

        if customers_affected != calculated_customers:
            raise ValueError(
                f"{self.name}: customers_affected does not match outages"
            )

        return data

    def parse_customer_count(self, value, field):
        """Parse a required count without coercing source errors to zero."""
        if isinstance(value, bool):
            raise ValueError(f"{self.name}: {field} is not a valid customer count")
        if isinstance(value, int):
            parsed = value
        elif isinstance(value, str) and re.fullmatch(
            r"(?:\d+|\d{1,3}(?:,\d{3})+)", value.strip()
        ):
            parsed = int(value.replace(",", ""))
        else:
            raise ValueError(f"{self.name}: {field} is not a valid customer count")
        if parsed < 0:
            raise ValueError(f"{self.name}: {field} must be non-negative")
        return parsed

    @staticmethod
    def _is_mst_timestamp(value):
        for date_format in (
            "%Y-%m-%d %H:%M:%S MST",
            "%Y-%m-%d %H:%M MST",
        ):
            try:
                datetime.strptime(value, date_format)
                return True
            except ValueError:
                continue
        return False

    @abstractmethod
    def fetch_data(self):
        pass
