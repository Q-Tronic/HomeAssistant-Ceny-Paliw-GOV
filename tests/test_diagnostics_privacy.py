"""Regression checks for privacy in diagnostics output."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "diagnostics.py"


class DiagnosticsPrivacyTests(unittest.TestCase):
    """Keep personal phone identifiers out of exported diagnostics."""

    def test_phone_identifiers_are_redacted(self) -> None:
        source = DIAGNOSTICS.read_text(encoding="utf-8")
        self.assertIn("async_redact_data", source)
        self.assertIn("DEVICE_SERVICE, DEVICE_NAME", source)
        self.assertIn("_phone_diagnostics", source)

    def test_missing_targets_are_reported_as_count_only(self) -> None:
        source = DIAGNOSTICS.read_text(encoding="utf-8")
        self.assertIn('"missing_enabled_targets_count"', source)
        self.assertNotIn('"missing_enabled_targets":', source)


if __name__ == "__main__":
    unittest.main()
