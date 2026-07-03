import unittest
from unittest.mock import patch

from scripts.run import run_providers


class FakeProvider:
    def __init__(self, name, result=None, error=None):
        self.name = name
        self.result = result
        self.error = error
        self.validated = False

    def fetch_data(self):
        if self.error:
            raise self.error
        return self.result

    def validate_snapshot(self, data):
        self.validated = True
        return data


class RunProvidersTests(unittest.TestCase):
    @patch("scripts.run.save_snapshot")
    def test_failure_does_not_block_later_providers(self, save_snapshot):
        failed = FakeProvider("failed", error=RuntimeError("unavailable"))
        successful = FakeProvider("successful", result={"ok": True})
        save_snapshot.return_value = (True, "snapshot.json")

        with self.assertRaisesRegex(RuntimeError, "Providers failed: failed"):
            run_providers([failed, successful])

        self.assertTrue(successful.validated)
        save_snapshot.assert_called_once_with("successful", {"ok": True})

    @patch("scripts.run.save_snapshot", return_value=(False, "latest.json"))
    def test_successful_run_does_not_raise(self, save_snapshot):
        provider = FakeProvider("working", result={"ok": True})

        run_providers([provider])

        save_snapshot.assert_called_once_with("working", {"ok": True})


if __name__ == "__main__":
    unittest.main()
