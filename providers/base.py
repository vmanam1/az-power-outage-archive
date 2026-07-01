from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseProvider(ABC):
    def __init__(self, name):
        self.name = name

    def build_metadata(self):
        return {
            "provider": self.name.upper(),
            "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "source": self.get_source(),
            "scraper_version": "1.0.0"
        }

    def get_source(self):
        return "Unknown"

    @abstractmethod
    def fetch_data(self):
        pass