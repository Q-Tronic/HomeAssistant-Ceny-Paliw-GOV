"""Regression tests for phone option normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"

# phone_config imports Home Assistant only for runtime type annotations/helpers.
# Minimal stubs are enough for pure normalization tests.
homeassistant = types.ModuleType("homeassistant")
config_entries = types.ModuleType("homeassistant.config_entries")
core = types.ModuleType("homeassistant.core")
config_entries.ConfigEntry = object
core.HomeAssistant = object
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.config_entries", config_entries)
sys.modules.setdefault("homeassistant.core", core)

package = types.ModuleType("ceny_paliw_gov_pl")
package.__path__ = [str(COMPONENT)]
sys.modules["ceny_paliw_gov_pl"] = package

for module_name in ("const", "phone_config"):
    spec = importlib.util.spec_from_file_location(
        f"ceny_paliw_gov_pl.{module_name}", COMPONENT / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

phone_config = sys.modules["ceny_paliw_gov_pl.phone_config"]


class PhoneConfigTests(unittest.TestCase):
    def test_single_target_string_is_not_split_into_characters(self) -> None:
        target = "notify.mobile_app_robert"
        self.assertEqual(phone_config.normalize_target_selection(target), [target])

    def test_multiple_targets_are_deduplicated_and_ordered(self) -> None:
        self.assertEqual(
            phone_config.normalize_target_selection(
                [
                    "notify.mobile_app_robert",
                    "notify.mobile_app_ania",
                    "notify.mobile_app_robert",
                ]
            ),
            ["notify.mobile_app_robert", "notify.mobile_app_ania"],
        )

    def test_empty_and_unknown_types_are_safe(self) -> None:
        self.assertEqual(phone_config.normalize_target_selection(None), [])
        self.assertEqual(phone_config.normalize_target_selection(123), [])


class ReloadRegressionTests(unittest.TestCase):
    def test_setup_does_not_register_update_listener_with_options_flow_reload(self) -> None:
        init_source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        flow_source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertIn("OptionsFlowWithReload", flow_source)
        self.assertNotIn("add_update_listener", init_source)
        self.assertNotIn("_async_options_update_listener", init_source)


if __name__ == "__main__":
    unittest.main()
