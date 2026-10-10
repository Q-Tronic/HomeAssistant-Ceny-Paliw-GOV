"""Regression checks for Config Flow diagnostic actions."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "config_flow.py"


class ConfigFlowSafetyTests(unittest.TestCase):
    def test_reconfigure_handles_invalid_stored_interval(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        flow = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "FuelPricesConfigFlow"
        )
        method = next(
            node for node in flow.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "async_step_reconfigure"
        )
        rendered = ast.unparse(method)
        self.assertIn("except (TypeError, ValueError)", rendered)
        self.assertIn("current_interval not in UPDATE_INTERVAL_MINUTES_OPTIONS", rendered)

    def test_diagnostics_refresh_checks_coordinator_result(self) -> None:
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        options_flow = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "FuelPricesOptionsFlow"
        )
        method = next(
            node for node in options_flow.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "async_step_diagnostics_refresh"
        )
        source = ast.unparse(method)
        self.assertIn("await coordinator.async_request_refresh()", source)
        self.assertIn("if not coordinator.last_update_success", source)
        self.assertIn("Błąd sprawdzania danych", source)


if __name__ == "__main__":
    unittest.main()
