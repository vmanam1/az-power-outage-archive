#!/usr/bin/env bash
#
# Raspberry Pi collector entrypoint.
#
# Runs the scraper, then commits and pushes any new snapshots. Mirrors the
# GitHub Actions job in .github/workflows/scrape.yml, but is driven by a
# systemd timer on the Pi instead (see deploy/systemd/). Data is therefore
# stored both locally on the Pi and pushed to GitHub.
#
# The scrape's exit code is preserved and returned so systemd records a run as
# failed when a provider fails, but snapshots from providers that DID succeed
# are still committed first (same "commit on always()" behaviour as CI).
#
# Environment (set by the systemd unit, with sensible fallbacks):
#   PYTHON             python interpreter to use (default: python3)
#   CHROME_BIN         Chromium binary for Selenium providers
#   CHROMEDRIVER_PATH  matching chromedriver for Selenium providers
set -uo pipefail

# Resolve repo root from this script's location so cron/systemd cwd doesn't matter.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT" || exit 1

PYTHON="${PYTHON:-python3}"

"$PYTHON" -m scripts.run
scrape_rc=$?

git add data/

if git diff --cached --quiet; then
    echo "No changes to commit."
else
    mst_time="$(TZ=America/Phoenix date '+%Y-%m-%d %H:%M MST')"
    git commit -m "Archive outage snapshot ${mst_time} (rpi)"
    git push
fi

exit "$scrape_rc"
