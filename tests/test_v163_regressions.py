"""Tests for v1.6.3 regressions without requiring Home Assistant Core."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"

homeassistant = types.ModuleType("homeassistant")
config_entries = types.ModuleType("homeassistant.config_entries")
core = types.ModuleType("homeassistant.core")
config_entries.ConfigEntry = object
core.HomeAssistant = object
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.core", core)
package = sys.modules.get("ceny_paliw_gov_pl")
if package is None:
    package = types.ModuleType("ceny_paliw_gov_pl")
    package.__path__ = [str(COMPONENT)]
    sys.modules["ceny_paliw_gov_pl"] = package
for module_name in ("const", "api", "phone_config"):
    name = f"ceny_paliw_gov_pl.{module_name}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, COMPONENT / f"{module_name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
api = sys.modules["ceny_paliw_gov_pl.api"]
phones = sys.modules["ceny_paliw_gov_pl.phone_config"]


class V163Tests(unittest.TestCase):
    def test_legacy_global_disabled_without_per_phone_settings(self):
        result = phones.normalized_options({
            "notifications_enabled": False,
            "notification_devices": [{"service": "notify.mobile_app_old", "enabled": True}],
        })
        self.assertFalse(result["notification_devices"][0]["enabled"])

    def test_independent_newer_phone_enabled_is_preserved(self):
        result = phones.normalized_options({
            "notifications_enabled": False,
            "notification_devices": [{
                "service": "notify.mobile_app_new",
                "enabled": True,
                "notification_time": "12:00:00",
                "fuels": ["on"],
            }],
        })
        self.assertTrue(result["notification_devices"][0]["enabled"])

    def test_merge_preserves_concurrent_dashboard_changes(self):
        original = {"notification_devices": [
            {"service": "notify.mobile_app_a", "name": "A", "enabled": True,
             "notification_time": "10:00:00", "fuels": ["pb95"]},
        ]}
        edited = {"notification_devices": [
            {"service": "notify.mobile_app_a", "name": "Nowa nazwa", "enabled": True,
             "notification_time": "10:00:00", "fuels": ["pb95"]},
        ]}
        latest = {"notification_devices": [
            {"service": "notify.mobile_app_a", "name": "A", "enabled": False,
             "notification_time": "10:00:00", "fuels": ["pb95"]},
        ]}
        result = phones.merge_working_options(original, edited, latest)
        device = result["notification_devices"][0]
        self.assertFalse(device["enabled"])
        self.assertEqual(device["name"], "Nowa nazwa")

    def test_recent_changed_price_format_is_detected(self):
        html = """<html><body>
            <div>11.10.2026</div>
            <a href="/web/energia/nowy-cennik">Maksymalna cena detaliczna paliw obowiązująca 12 października 2026 r.</a>
            <p>Benzyna 95: 7,10 PLN/l, benzyna 98: 8,10 PLN/l, olej napędowy: 8,20 PLN/l.</p>
            <div>10.10.2026</div>
            <a href="/web/energia/stary-cennik">Maksymalna cena detaliczna paliw obowiązująca 11 października 2026 r.</a>
            <p>Benzyna 95 - 7,00 zł/l, benzyna 98 - 8,00 zł/l, olej napędowy - 8,10 zł/l.</p>
            </body></html>"""
        result = api._parse_news_page_diagnostics(html)
        self.assertEqual(len(result.periods), 1)
        self.assertTrue(any(x.published_on == date(2026, 10, 11) for x in result.rejected))

    def test_manifest_sort_hassfest(self):
        import json
        obj = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(list(obj)[:2], ["domain", "name"])
        self.assertEqual(list(obj)[2:], sorted(list(obj)[2:]))

    def test_binary_sensor_has_unknown_state_when_prices_missing(self):
        source = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
        self.assertIn("return None if difference is None else difference > 0", source)

    def test_entry_removal_cleans_local_stores(self):
        source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("async def async_remove_entry", source)
        self.assertEqual(source.count(").async_remove()"), 2)


if __name__ == "__main__":
    unittest.main()
