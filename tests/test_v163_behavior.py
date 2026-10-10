"""Focused behavior checks for v1.6.3 using isolated Home Assistant mocks.

These are NOT substitutes for tests in a running Home Assistant instance.
"""
from __future__ import annotations

import ast
import asyncio
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "ceny_paliw_gov_pl"


def load_functions(filename: str, names: set[str], globals_: dict):
    """Compile the original functions with test-provided dependency objects."""
    path = COMPONENT / filename
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [
        x for x in tree.body
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name in names
    ]
    assert len(nodes) == len(names), (filename, names)
    code = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(code)
    namespace = dict(globals_)
    exec(compile(code, str(path), "exec"), namespace)
    return namespace


def load_binary_sensor():
    filename = COMPONENT / "binary_sensor.py"
    tree = ast.parse(filename.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "FuelMoreExpensiveBinarySensor")
    methods = [x for x in cls.body if isinstance(x, ast.FunctionDef)
               and x.name in {"_difference", "is_on"}]
    mini = ast.ClassDef(name="MiniBinarySensor", bases=[], keywords=[],
                        body=methods, decorator_list=[])
    code = ast.Module(body=[mini], type_ignores=[])
    ast.fix_missing_locations(code)
    namespace = {"Decimal": Decimal}
    exec(compile(code, str(filename), "exec"), namespace)
    return namespace["MiniBinarySensor"]


class BinarySensorBehaviorTests(unittest.TestCase):
    def test_unknown_when_comparison_is_unavailable(self):
        sensor = load_binary_sensor()()
        sensor.fuel = "pb95"
        sensor.coordinator = SimpleNamespace(data=SimpleNamespace(today=None, tomorrow=None))
        self.assertIsNone(sensor.is_on)
        sensor.coordinator.data.today = SimpleNamespace(prices={"pb95": Decimal("6.00")})
        self.assertIsNone(sensor.is_on)

    def test_rising_falling_equal_prices(self):
        sensor = load_binary_sensor()()
        sensor.fuel = "pb95"
        for future, expected in (("6.01", True), ("5.99", False), ("6.00", False)):
            sensor.coordinator = SimpleNamespace(data=SimpleNamespace(
                today=SimpleNamespace(prices={"pb95": Decimal("6.00")}),
                tomorrow=SimpleNamespace(prices={"pb95": Decimal(future)}),
            ))
            self.assertIs(sensor.is_on, expected)


class TemplateFallbackBehaviorTests(unittest.TestCase):
    def test_unexpected_error_uses_default_message(self):
        class BrokenTemplate:
            def __init__(self, *_):
                pass

            def async_render(self, **_):
                raise ValueError("nieoczekiwany błąd szablonu")

        calls = []
        namespace = load_functions("notifications.py", {"_render_custom_template"}, {
            "Template": BrokenTemplate,
            "_LOGGER": SimpleNamespace(error=lambda *args: calls.append(args)),
        })
        self.assertIsNone(namespace["_render_custom_template"](None, "{{ test }}", {}))
        self.assertTrue(calls)

    def test_empty_template_is_ignored(self):
        namespace = load_functions("notifications.py", {"_render_custom_template"}, {
            "Template": None,
            "_LOGGER": None,
        })
        self.assertIsNone(namespace["_render_custom_template"](None, "   ", {}))


class RemovalBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_removing_entry_removes_both_stores_and_parser_repair(self):
        removed = []

        class StubStore:
            def __init__(self, hass, version, key):
                self.key = key

            async def async_remove(self):
                removed.append(self.key)

        issues = []
        namespace = load_functions("__init__.py", {"async_remove_entry"}, {
            "Store": StubStore,
            "HISTORY_STORAGE_VERSION": 1,
            "NOTIFICATION_STORAGE_VERSION": 1,
            "HISTORY_STORAGE_KEY_PREFIX": "ceny_paliw_gov_pl.history",
            "NOTIFICATION_STORAGE_KEY_PREFIX": "ceny_paliw_gov_pl.notification_state",
            "DOMAIN": "ceny_paliw_gov_pl",
            "ir": SimpleNamespace(async_delete_issue=lambda *a: issues.append(a)),
        })
        await namespace["async_remove_entry"](object(), SimpleNamespace(entry_id="test-entry"))
        self.assertCountEqual(removed, [
            "ceny_paliw_gov_pl.history.test-entry",
            "ceny_paliw_gov_pl.notification_state.test-entry",
        ])
        self.assertTrue(any(x[1:] == ("ceny_paliw_gov_pl", "parser_error") for x in issues))


if __name__ == "__main__":
    unittest.main()
