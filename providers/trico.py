from providers.coop import CoopOutageMapProvider


class TricoProvider(CoopOutageMapProvider):
    # https://trico.outagemap.coop
    SLUG = "trico"

    def __init__(self):
        super().__init__("trico")
