import time

import requests


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def request_with_retries(request, url, retries=3, backoff_seconds=1, **kwargs):
    """Run an HTTP request with bounded exponential backoff."""
    for attempt in range(retries):
        try:
            response = request(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            retryable = isinstance(
                exc, (requests.Timeout, requests.ConnectionError)
            ) or status in RETRYABLE_STATUS_CODES

            if not retryable or attempt == retries - 1:
                raise

            time.sleep(backoff_seconds * (2 ** attempt))

    raise RuntimeError("HTTP retry loop exited unexpectedly")
