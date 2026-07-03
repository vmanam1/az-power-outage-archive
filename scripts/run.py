from providers.aps import APSProvider
from scripts.archive import save_snapshot
from scripts.logger import logger
from providers.srp import SRPProvider
from providers.ssvec import SSVECProvider
from providers.ed3 import ED3Provider
from providers.mohave import MohaveProvider
from providers.navopache import NavopacheProvider
from providers.trico import TricoProvider

def main():

    providers = [
        APSProvider(),
        SRPProvider(),
        SSVECProvider(),
        TricoProvider(),
        ED3Provider(),
        MohaveProvider(),
        NavopacheProvider(),
    ]

    for provider in providers:

        logger.info(f"Fetching {provider.name}...")

        data = provider.fetch_data()

        saved, path = save_snapshot(
            provider.name,
            data
        )

        if saved:
            logger.info(f"Saved snapshot: {path}")
        else:
            logger.info(f"No changes detected. Latest snapshot: {path}")


if __name__ == "__main__":
    main()
