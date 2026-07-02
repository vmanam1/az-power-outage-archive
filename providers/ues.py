from providers.tep import TEPProvider


class UESProvider(TEPProvider):
    """UniSource electric outages for Santa Cruz and Mohave counties."""

    DIVISIONS = frozenset({"USE", "UEE"})
    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.uesaz.com",
        "Referer": "https://www.uesaz.com/electric-outage-map/",
        "User-Agent": "az-power-outage-archive/1.0",
    }

    def __init__(self):
        super().__init__()
        self.name = "ues"

    def get_source(self):
        return "UniSource Electric Outage Map Feed"
