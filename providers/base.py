from abc import ABC, abstractmethod


class BaseProvider(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def fetch_data(self):
        """
        Fetch outage data from the provider.

        Returns:
            dict: Standardized outage data.
        """
        pass