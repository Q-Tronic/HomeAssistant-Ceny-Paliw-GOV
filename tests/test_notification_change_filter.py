"""Regression tests for change-only notification mode filtering."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "notifications.py"


def _load_filter_functions() -> dict[str, object]:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    wanted = {"_price", "difference_grosz", "selected_fuels", "has_relevant_change"}
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    source = (
        "from __future__ import annotations\n"
        "from decimal import Decimal, ROUND_HALF_UP\n"
        + "\n".join(ast.unparse(node) for node in selected)
    )

    def normalize_fuels(value: object) -> list[str]:
        allowed = ("pb95", "pb98", "on")
        if not isinstance(value, (list, tuple, set)):
            return list(allowed)
        selected_values = {str(item) for item in value if str(item) in allowed}
        return [fuel for fuel in allowed if fuel in selected_values] or list(allowed)

    namespace: dict[str, object] = {
        "FUELS": ("pb95", "pb98", "on"),
        "CONF_NOTIFICATION_FUELS": "notification_fuels",
        "CONF_NOTIFICATION_ONLY_ON_CHANGE": "notification_only_on_change",
        "CONF_NOTIFICATION_MIN_CHANGE_GROSZ": "notification_min_change_grosz",
        "DEFAULT_NOTIFICATION_ONLY_ON_CHANGE": False,
        "DEFAULT_NOTIFICATION_MIN_CHANGE_GROSZ": 0,
        "normalize_fuels": normalize_fuels,
    }
    exec(compile(source, str(MODULE), "exec"), namespace)
    return namespace


class NotificationChangeFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.functions = _load_filter_functions()

    @staticmethod
    def _data(today: str, tomorrow: str) -> SimpleNamespace:
        return SimpleNamespace(
            today=SimpleNamespace(prices={"pb95": Decimal(today)}),
            tomorrow=SimpleNamespace(prices={"pb95": Decimal(tomorrow)}),
        )

    def test_force_mode_filters_unchanged_price_even_when_global_filter_is_off(self) -> None:
        has_change = self.functions["has_relevant_change"]
        self.assertFalse(
            has_change(
                self._data("6.97", "6.97"),
                {"notification_only_on_change": False},
                fuels_override=["pb95"],
                force=True,
            )
        )

    def test_force_mode_uses_minimum_change_threshold(self) -> None:
        has_change = self.functions["has_relevant_change"]
        options = {
            "notification_only_on_change": False,
            "notification_min_change_grosz": 5,
        }
        self.assertFalse(
            has_change(
                self._data("6.97", "7.00"),
                options,
                fuels_override=["pb95"],
                force=True,
            )
        )
        self.assertTrue(
            has_change(
                self._data("6.97", "7.02"),
                options,
                fuels_override=["pb95"],
                force=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
