"""Regression tests for default notification message formatting."""

from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "notifications.py"


def _load_formatting_functions() -> dict[str, object]:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    wanted = {
        "_format_price",
        "_price",
        "difference_grosz",
        "change_text",
        "build_price_notification",
        "build_not_published_notification",
    }
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in wanted
    ]
    source = (
        "from __future__ import annotations\n"
        "from decimal import Decimal, ROUND_HALF_UP\n"
        + "\n".join(ast.unparse(node) for node in selected)
    )
    namespace: dict[str, object] = {
        "STATUS_NOT_PUBLISHED": "Nie opublikowano",
        "STATUS_NO_CHANGE": "bez zmian",
        "UNIT_PRICE": "zł/l",
        "FUELS": ("pb95", "pb98", "on"),
        "FUEL_NAMES": {"pb95": "PB95", "pb98": "PB98", "on": "ON"},
    }
    exec(compile(source, str(MODULE), "exec"), namespace)
    return namespace


class NotificationFormattingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.functions = _load_formatting_functions()

    def _data(self, tomorrow: bool = True) -> SimpleNamespace:
        prices = {
            "pb95": Decimal("6.97"),
            "pb98": Decimal("7.85"),
            "on": Decimal("8.06"),
        }
        period = SimpleNamespace(prices=prices)
        return SimpleNamespace(
            tomorrow_date=date(2026, 10, 11),
            today=period,
            tomorrow=period if tomorrow else None,
        )

    def test_published_message_has_no_blank_line(self) -> None:
        build = self.functions["build_price_notification"]
        message = build(self._data())
        self.assertNotIn("\n\n", message)
        self.assertEqual(
            message.splitlines()[1],
            "PB95: dziś 6,97 zł/l, jutro 6,97 zł/l, bez zmian",
        )

    def test_not_published_message_has_no_blank_line(self) -> None:
        build = self.functions["build_not_published_notification"]
        message = build(self._data(tomorrow=False))
        self.assertNotIn("\n\n", message)
        self.assertEqual(
            message,
            "Maksymalne ceny paliw na jutro, 11.10.2026\n"
            "Ministerstwo Energii nie opublikowało jeszcze cen na jutro.",
        )


if __name__ == "__main__":
    unittest.main()
