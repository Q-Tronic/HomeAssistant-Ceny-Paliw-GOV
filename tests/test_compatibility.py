"""Static compatibility checks for supported Home Assistant versions."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"


class CompatibilityTests(unittest.TestCase):
    def test_config_flow_uses_voluptuous_compatibility_import(self) -> None:
        source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertIn("import voluptuous as vol", source)
        self.assertNotIn("import probatio", source)
        self.assertNotIn("probatio.", source)

    def test_custom_integration_does_not_ship_strings_json(self) -> None:
        self.assertFalse((COMPONENT / "strings.json").exists())
        self.assertTrue((COMPONENT / "translations" / "en.json").exists())
        self.assertTrue((COMPONENT / "translations" / "pl.json").exists())

    def test_hacs_declares_minimum_home_assistant_version(self) -> None:
        data = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        self.assertEqual(data.get("homeassistant"), "2025.8.0")

    def test_entity_category_uses_public_const_import(self) -> None:
        for name in ("button.py", "select.py", "sensor.py", "switch.py", "time.py"):
            source = (COMPONENT / name).read_text(encoding="utf-8")
            with self.subTest(file=name):
                self.assertIn("from homeassistant.const import EntityCategory", source)
                self.assertNotIn("from homeassistant.helpers.entity import EntityCategory", source)


if __name__ == "__main__":
    unittest.main()
