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

    @abstractmethod
    def fetch_data(self):
        pass
