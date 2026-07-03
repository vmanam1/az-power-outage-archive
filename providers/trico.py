from providers.nisc import NISCOutageProvider


class TricoProvider(NISCOutageProvider):
    MAP_URL = "https://ebill.trico.org/maps/Trico_External/OutageWebMap/"

    def __init__(self):
        super().__init__("trico")
