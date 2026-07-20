from providers.aps import APSProvider
from scripts.archive import save_snapshot
from scripts.logger import logger
from scripts.utils import current_time
from providers.srp import SRPProvider
from providers.ssvec import SSVECProvider
from providers.ed3 import ED3Provider
from providers.mohave import MohaveProvider
from providers.navopache import NavopacheProvider
from providers.trico import TricoProvider
from providers.tep import TEPProvider
from providers.ues import UESProvider

def run_providers(providers, scraped_at=None):
    # Capture one timestamp for the whole run so every provider in this cycle
    # records an identical scrape time (and therefore an identical snapshot
    # filename minute), instead of each provider stamping its own save moment.
    scraped_at = scraped_at or current_time()
    failures = []

    for provider in providers:
        logger.info(f"Fetching {provider.name}...")
        provider.scraped_at = scraped_at

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
