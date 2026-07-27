from providers.coop import CoopOutageMapProvider


class MohaveProvider(CoopOutageMapProvider):
    # https://mohaveelectric.outagemap.coop
    SLUG = "mohaveelectric"

    def __init__(self):
        super().__init__("mohave")
