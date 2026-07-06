from providers.aps import APSProvider
from scripts.archive import save_snapshot
from scripts.logger import logger
from providers.srp import SRPProvider
from providers.ssvec import SSVECProvider
from providers.ed3 import ED3Provider
from providers.mohave import MohaveProvider
from providers.navopache import NavopacheProvider
from providers.trico import TricoProvider
from providers.tep import TEPProvider
from providers.ues import UESProvider

def run_providers(providers):
    failures = []

    for provider in providers:
        logger.info(f"Fetching {provider.name}...")

        try:
            data = provider.fetch_data()
            provider.validate_snapshot(data)
            summary = data["summary"]
            logger.info(
                "%s quality check passed: %s outages, %s customers affected",
                provider.name,
                summary["outage_count"],
                summary["customers_affected"],
            )
            saved, path = save_snapshot(provider.name, data)
        except Exception:
            logger.exception(f"Failed to archive {provider.name}")
            failures.append(provider.name)
            continue

        if saved:
            logger.info(f"Saved snapshot: {path}")
        else:
            logger.info(f"No changes detected. Latest snapshot: {path}")

    if failures:
        raise RuntimeError(f"Providers failed: {', '.join(failures)}")


def main():
    providers = [
        APSProvider(),
        SRPProvider(),
        TEPProvider(),
        UESProvider(),
        SSVECProvider(),
        TricoProvider(),
        ED3Provider(),
        MohaveProvider(),
        NavopacheProvider(),
    ]

    run_providers(providers)


if __name__ == "__main__":
    main()
