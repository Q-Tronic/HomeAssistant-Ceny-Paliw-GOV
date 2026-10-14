"""Regressions for numeric sensors with missing GOV.PL data.

Uses the actual methods extracted from sensor.py without importing HA Core; this
is a behavior test, not a full runtime Home Assistant integration test.
"""
from __future__ import annotations

import ast
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "ceny_paliw_gov_pl"


def load_sensor_class(source_class: str, methods: set[str]):
    """Execute selected original sensor methods in an isolated test class."""
    path = COMPONENT / "sensor.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    original = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == source_class
    )
    selected = [
        node for node in original.body
        if isinstance(node, ast.FunctionDef) and node.name in methods
    ]
    assert len(selected) == len(methods), (source_class, methods)
    cls = ast.ClassDef(
        name="Mini" + source_class, bases=[], keywords=[],
        body=selected, decorator_list=[],
    )
    compiled = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        cls,
    ], type_ignores=[])
    ast.fix_missing_locations(compiled)
    scope = {
        "FUEL_NAMES": {"pb95": "PB95", "pb98": "PB98", "on": "ON"},
        "STATUS_NOT_PUBLISHED": "Nie opublikowano",
        "STATUS_NO_CHANGE": "bez zmian",
        "NEWS_URL": "https://www.gov.pl/web/energia/wiadomosci",
        "UNIT_PRICE": "zł/l",
        "Decimal": Decimal,
    }
    exec(compile(compiled, str(path), "exec"), scope)
    return scope[cls.name]


PriceSensor = load_sensor_class("FuelPriceSensor", {
    "native_value", "native_unit_of_measurement", "extra_state_attributes",
    "_period_for_day", "_change_state", "_difference", "_difference_grosz",
})
AverageSensor = load_sensor_class("FuelHistoryAverageSensor", {
    "_summary", "native_value", "native_unit_of_measurement", "extra_state_attributes",
})


def period(prices: dict):
    return SimpleNamespace(
        prices=prices,
        valid_from=date(2026, 10, 14),
        valid_to=date(2026, 10, 14),
        published_on=date(2026, 10, 13),
        source_url="https://www.gov.pl/web/energia/przykladowa-publikacja",
    )


def sensor(fuel: str, day: str, today, tomorrow):
    entity = PriceSensor()
    entity.entity_description = SimpleNamespace(fuel=fuel, day=day, kind="price")
    entity.coordinator = SimpleNamespace(data=SimpleNamespace(
        today=today,
        tomorrow=tomorrow,
        today_date=date(2026, 10, 14),
        tomorrow_date=date(2026, 10, 15),
        fetched_at=datetime(2026, 10, 14, 11, tzinfo=timezone.utc),
    ))
    return entity


class NumericPriceSensorTests(unittest.TestCase):
    def test_unpublished_tomorrow_returns_none_for_every_fuel(self):
        for fuel in ("pb95", "pb98", "on"):
            with self.subTest(fuel=fuel):
                entity = sensor(fuel, "tomorrow", period({fuel: Decimal("7.01")}), None)
                self.assertIsNone(entity.native_value)
                self.assertIsNone(entity.native_unit_of_measurement)
                self.assertEqual(entity.extra_state_attributes["status_danych"], "nie_opublikowano")
                self.assertEqual(entity.extra_state_attributes["oczekiwana_data"], "2026-10-15")

    def test_missing_today_is_also_numeric_none(self):
        entity = sensor("on", "today", None, None)
        self.assertIsNone(entity.native_value)
        self.assertEqual(entity.extra_state_attributes["status_danych"], "nie_opublikowano")

    def test_missing_one_fuel_in_a_published_period(self):
        future = period({"pb95": Decimal("7.11")})
        for fuel in ("pb98", "on"):
            with self.subTest(fuel=fuel):
                entity = sensor(fuel, "tomorrow", None, future)
                self.assertIsNone(entity.native_value)
                self.assertIsNone(entity.native_unit_of_measurement)
                self.assertEqual(entity.extra_state_attributes["status_danych"], "nie_opublikowano")
                self.assertIsNone(entity.extra_state_attributes["cena_numeryczna"])

    def test_published_price_is_still_float_with_correct_unit(self):
        for fuel, amount in (("pb95", "7.11"), ("pb98", "8.01"), ("on", "7.98")):
            with self.subTest(fuel=fuel):
                entity = sensor(fuel, "today", period({fuel: Decimal(amount)}), None)
                self.assertEqual(entity.native_value, float(amount))
                self.assertEqual(entity.native_unit_of_measurement, "zł/l")
                self.assertEqual(entity.extra_state_attributes["status_danych"], "opublikowano")

    def test_change_sensor_keeps_human_readable_status(self):
        entity = sensor("pb95", "tomorrow", None, None)
        entity.entity_description.kind = "change"
        self.assertEqual(entity.native_value, "Nie opublikowano")


class NumericAverageSensorTests(unittest.TestCase):
    @staticmethod
    def entity(average):
        values = {
            "average": average,
            "samples": 0 if average is None else 1,
            "minimum": average, "maximum": average,
            "first": average, "last": average,
            "change": None, "change_percent": None,
        }
        e = AverageSensor()
        e.fuel = "pb95"
        e.days = 7
        e.history = SimpleNamespace(
            summary=lambda *args: values,
            available_days=lambda *args: 0 if average is None else 1,
        )
        e.coordinator = SimpleNamespace(data=SimpleNamespace(today_date=date(2026, 10, 14)))
        return e

    def test_empty_history_never_returns_a_text_state(self):
        entity = self.entity(None)
        for days in (7, 30, 90):
            with self.subTest(days=days):
                entity.days = days
                self.assertIsNone(entity.native_value)
                self.assertIsNone(entity.native_unit_of_measurement)
                self.assertEqual(entity.extra_state_attributes["status_danych"], "brak_historii")

    def test_available_history_still_returns_numeric_average(self):
        entity = self.entity(Decimal("7.22"))
        self.assertEqual(entity.native_value, 7.22)
        self.assertEqual(entity.native_unit_of_measurement, "zł/l")
        self.assertEqual(entity.extra_state_attributes["status_danych"], "opublikowano")


if __name__ == "__main__":
    unittest.main()
