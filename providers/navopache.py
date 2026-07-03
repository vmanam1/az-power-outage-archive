from providers.nisc import NISCOutageProvider


class NavopacheProvider(NISCOutageProvider):
    MAP_URL = "https://ebill1.navopache.org/maps/OutageWebMap/"

    def __init__(self):
        super().__init__("navopache")
