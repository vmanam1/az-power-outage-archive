from providers.coop import CoopOutageMapProvider


class GarkaneProvider(CoopOutageMapProvider):
    """
    Garkane Energy Cooperative (Loa, UT) serves the Arizona Strip --
    Fredonia, Colorado City, and Marble Canyon -- alongside its southern
    Utah territory. The runner's Arizona filter keeps only the AZ records.
    """

    SLUG = "garkaneenergy"

    def __init__(self):
        super().__init__("garkane")
