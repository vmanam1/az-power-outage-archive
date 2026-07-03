from abc import ABC, abstractmethod

from scripts.utils import current_time


class BaseProvider(ABC):
    def __init__(self, name):
        self.name = name

    def build_metadata(self):
        return {
            "provider": self.name.upper(),
            "scraped_at": current_time(),
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
        if not isinstance(summary, dict):
            raise ValueError(f"{self.name}: summary must be an object")
        if not isinstance(outages, list):
            raise ValueError(f"{self.name}: outages must be a list")

        outage_count = summary.get("outage_count")
        customers_affected = summary.get("customers_affected")
        if not isinstance(outage_count, int) or outage_count < 0:
            raise ValueError(f"{self.name}: outage_count must be non-negative")
        if not isinstance(customers_affected, int) or customers_affected < 0:
            raise ValueError(
                f"{self.name}: customers_affected must be non-negative"
            )
        if outage_count != len(outages):
            raise ValueError(f"{self.name}: outage_count does not match outages")

        calculated_customers = 0
        for index, outage in enumerate(outages):
            if not isinstance(outage, dict):
                raise ValueError(f"{self.name}: outage {index} must be an object")

            customers = outage.get("customers")
            if not isinstance(customers, int) or customers < 0:
                raise ValueError(
                    f"{self.name}: outage {index} has invalid customers"
                )
            calculated_customers += customers

            latitude = outage.get("latitude")
            longitude = outage.get("longitude")
            if latitude is not None and (
                not isinstance(latitude, (int, float)) or not -90 <= latitude <= 90
            ):
                raise ValueError(
                    f"{self.name}: outage {index} has invalid latitude"
                )
            if longitude is not None and (
                not isinstance(longitude, (int, float))
                or not -180 <= longitude <= 180
            ):
                raise ValueError(
                    f"{self.name}: outage {index} has invalid longitude"
                )

        if customers_affected != calculated_customers:
            raise ValueError(
                f"{self.name}: customers_affected does not match outages"
            )

        return data

    @abstractmethod
    def fetch_data(self):
        pass
