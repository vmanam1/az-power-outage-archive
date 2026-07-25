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

# Preflight: the NISC (Selenium) providers need Chromium and chromedriver at the
# SAME major version. apt can upgrade one without the other, which silently
# breaks those three providers while the other six still commit+push -- so the
# dead-man's-switch would stay green on a partial failure. Detect a mismatch and
# flag it loudly (and via a fail ping below) so it does not go unnoticed.
drift_detected=0
_chrome_bin="${CHROME_BIN:-chromium}"
_driver_bin="${CHROMEDRIVER_PATH:-chromedriver}"
if command -v "$_chrome_bin" >/dev/null 2>&1 && command -v "$_driver_bin" >/dev/null 2>&1; then
    _chrome_major="$("$_chrome_bin" --version 2>/dev/null | grep -oE '[0-9]+' | head -1)"
    _driver_major="$("$_driver_bin" --version 2>/dev/null | grep -oE '[0-9]+' | head -1)"
    if [ -n "$_chrome_major" ] && [ -n "$_driver_major" ] && [ "$_chrome_major" != "$_driver_major" ]; then
        echo "ERROR: Chromium ($_chrome_major) and chromedriver ($_driver_major) major versions differ;" \
             "the NISC providers (trico/mohave/navopache) will fail." \
             "Fix with: sudo apt install chromium chromium-driver"
        drift_detected=1
    fi
fi

"$PYTHON" -m scripts.run
scrape_rc=$?

git add data/

run_ok=1
if git diff --cached --quiet; then
    echo "No changes to commit."
else
    mst_time="$(TZ=America/Phoenix date '+%Y-%m-%d %H:%M MST')"
    git commit -m "Archive outage snapshot ${mst_time} (rpi)"

    # Push, reconciling with any commits that landed on the remote since our
    # last fetch (a concurrent committer or a manual push). Our commits only
    # add new per-timestamp files, so the rebase is normally conflict-free.
    pushed=0
    for attempt in 1 2 3; do
        if git push; then
            pushed=1
            break
        fi
        echo "push rejected (attempt ${attempt}); rebasing on origin/main and retrying"
        git pull --rebase origin main || break
    done
    if [ "$pushed" -ne 1 ]; then
        echo "WARNING: could not push snapshot after retries; committed locally only."
        run_ok=0
    fi
fi

# Dead-man's-switch ping (healthchecks.io). Signals that the collector RAN and
# stored/pushed data, independent of whether an individual provider (e.g.
# navopache) was down -- so a MISSED ping means a genuine collector problem
# (Pi offline, hang/timeout, push/auth failure), not an upstream outage, and
# avoids hourly false alarms while a provider is down. HEALTHCHECK_URL is
# injected out-of-band (see /etc/default/outage-archive on the Pi) to keep the
# ping token out of this public repo. Unset -> pinging is skipped.
if [ -n "${HEALTHCHECK_URL:-}" ]; then
    if [ "$run_ok" -eq 1 ] && [ "$drift_detected" -eq 0 ]; then
        curl -fsS -m 10 --retry 3 -o /dev/null "${HEALTHCHECK_URL}" || true
    else
        curl -fsS -m 10 --retry 3 -o /dev/null "${HEALTHCHECK_URL%/}/fail" || true
    fi
fi

exit "$scrape_rc"
