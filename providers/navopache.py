from providers.coop import CoopOutageMapProvider


class NavopacheProvider(CoopOutageMapProvider):
    # https://navopache.outagemap.coop
    SLUG = "navopache"

    def __init__(self):
        super().__init__("navopache")
