import unittest
from unittest.mock import Mock, patch

import requests

from scripts.http import request_with_retries


class RequestWithRetriesTests(unittest.TestCase):
    @patch("scripts.http.time.sleep")
    def test_retries_transient_failures_with_exponential_backoff(self, sleep):
        response = Mock()
        request = Mock(
            side_effect=[
                requests.Timeout("first"),
                requests.ConnectionError("second"),
                response,
            ]
        )

        result = request_with_retries(request, "https://example.com", timeout=30)

        self.assertIs(result, response)
        self.assertEqual(request.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])

    @patch("scripts.http.time.sleep")
    def test_does_not_retry_non_transient_http_error(self, sleep):
        response = Mock(status_code=404)
        error = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = error
        request = Mock(return_value=response)

        with self.assertRaises(requests.HTTPError):
            request_with_retries(request, "https://example.com")

        request.assert_called_once_with("https://example.com")
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
