from providers.coop import CoopOutageMapProvider


class DixieProvider(CoopOutageMapProvider):
    """
    Dixie Power (St. George, UT) serves Arizona's far northwest corner --
    Beaver Dam, Littlefield, and Scenic along the Virgin River. Most of its
    territory is in Utah; the runner's Arizona filter keeps only the AZ
    records.
    """

    SLUG = "dixiepower"

    def __init__(self):
        super().__init__("dixie")
