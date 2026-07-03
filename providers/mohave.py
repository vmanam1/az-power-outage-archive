from providers.nisc import NISCOutageProvider


class MohaveProvider(NISCOutageProvider):
    MAP_URL = "https://ebill.mohaveelectric.com/maps/OutageWebMap/"

    def __init__(self):
        super().__init__("mohave")
