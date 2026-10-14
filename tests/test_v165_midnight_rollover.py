"""Regression tests for midnight rollover independent of HA runtime.

These exercise the original coordinator rollover and fingerprint methods.
"""
from __future__ import annotations

import ast
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from dataclasses import dataclass, replace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"


@dataclass(frozen=True)
class PricePeriod:
    valid_from: date
    valid_to: date
    prices: dict
    source_url: str = "gov"
    published_on: date | None = None
    def contains(self, target):
        return self.valid_from <= target <= self.valid_to


@dataclass(frozen=True)
class FuelPriceData:
    today_date: date
    tomorrow_date: date
    today: PricePeriod | None
    tomorrow: PricePeriod | None
    fetched_at: datetime
    parsed_periods: int
    periods: tuple[PricePeriod, ...]


def _resolve_period(periods, target):
    matches = [period for period in periods if period.contains(target)]
    if not matches:
        return None
    return max(matches, key=lambda item: (
        item.published_on or date.min, item.valid_from, item.valid_to
    ))


def coordinator_class():
    source = COMPONENT / "coordinator.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    orig = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FuelPriceCoordinator")
    wanted = {"rollover_to_local_date", "_data_for_local_date", "_fingerprint", "_period_fingerprint"}
    methods = [node for node in orig.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    assert len(methods) == len(wanted)
    clas = ast.ClassDef(name="RolloverCoordinator", bases=[], keywords=[], body=methods, decorator_list=[])
    mod = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), clas], type_ignores=[])
    ast.fix_missing_locations(mod)
    scope = {"replace": replace, "timedelta": timedelta, "date": date, "_resolve_period": _resolve_period}
    exec(compile(mod, str(source), "exec"), scope)
    return scope["RolloverCoordinator"]


Coordinator = coordinator_class()


def make_coordinator(periods, day=date(2026, 10, 14)):
    self = Coordinator()
    today = _resolve_period(periods, day)
    tomorrow = _resolve_period(periods, day + timedelta(days=1))
    self.data = FuelPriceData(day, day + timedelta(days=1), today, tomorrow,
                              datetime(2026, 10, 14, 11, tzinfo=timezone.utc), len(periods), tuple(periods))
    self._last_data_fingerprint = self._fingerprint(self.data)
    self.updates = []
    self.events = []
    def set_updated_data(data):
        self.data = data
        self.updates.append(data)
    self.async_set_updated_data = set_updated_data
    self._fire_update_event = lambda data: self.events.append(data)
    return self


class MidnightRolloverTests(unittest.TestCase):
    def test_tomorrows_price_becomes_todays_price_without_network(self):
        old = PricePeriod(date(2026,10,14), date(2026,10,14), {"on": Decimal("7.98")})
        new = PricePeriod(date(2026,10,15), date(2026,10,15), {"on": Decimal("8.05")})
        c = make_coordinator((new,old))
        fetched = c.data.fetched_at
        self.assertTrue(c.rollover_to_local_date(date(2026,10,15)))
        self.assertIs(c.data.today,new)
        self.assertIsNone(c.data.tomorrow)
        self.assertEqual(c.data.tomorrow_date,date(2026,10,16))
        self.assertEqual(c.data.fetched_at, fetched)
        self.assertEqual(len(c.events),1)
        self.assertEqual(c._last_data_fingerprint,c._fingerprint(c.data))

    def test_multi_day_validity_is_used_on_both_days(self):
        period = PricePeriod(date(2026,10,14), date(2026,10,18), {"on":Decimal("8.06")})
        c = make_coordinator((period,))
        self.assertTrue(c.rollover_to_local_date(date(2026,10,15)))
        self.assertIs(c.data.today,period)
        self.assertIs(c.data.tomorrow,period)

    def test_expired_period_does_not_leak_into_next_day(self):
        period = PricePeriod(date(2026,10,14), date(2026,10,14), {"on":Decimal("7.98")})
        c = make_coordinator((period,))
        self.assertTrue(c.rollover_to_local_date(date(2026,10,15)))
        self.assertIsNone(c.data.today)
        self.assertIsNone(c.data.tomorrow)

    def test_repeated_callback_same_day_does_not_emit_duplicate_event(self):
        c = make_coordinator(())
        self.assertFalse(c.rollover_to_local_date(date(2026,10,14)))
        self.assertEqual(c.events,[])
        self.assertTrue(c.rollover_to_local_date(date(2026,10,15)))
        self.assertFalse(c.rollover_to_local_date(date(2026,10,15)))
        self.assertEqual(len(c.events),1)

    def test_corrected_publication_wins_when_ranges_overlap(self):
        old = PricePeriod(date(2026,10,15), date(2026,10,16), {"on": Decimal("8.05")},published_on=date(2026,10,13))
        new = PricePeriod(date(2026,10,15), date(2026,10,16), {"on": Decimal("8.06")},published_on=date(2026,10,14))
        c = make_coordinator((old,new))
        c.rollover_to_local_date(date(2026,10,15))
        self.assertIs(c.data.today,new)

    def test_midnight_listener_created_at_local_midnight_and_unsubscribed(self):
        source = (COMPONENT/"__init__.py").read_text(encoding="utf-8")
        self.assertIn("async_track_time_change(",source)
        self.assertIn("hour=0, minute=0, second=1",source)
        self.assertIn("dt_util.now().date()",source)
        self.assertIn("coordinator.async_request_refresh()",source)
        self.assertIn("entry.async_on_unload(",source)

    def test_midnight_callback_rebases_before_scheduling_refresh(self):
        import asyncio
        source = COMPONENT / "__init__.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        setup = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry")
        callback = next(node for node in setup.body if isinstance(node, ast.FunctionDef) and node.name == "_handle_local_midnight")
        callback.decorator_list = []
        mod = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), callback], type_ignores=[])
        ast.fix_missing_locations(mod)
        events = []
        class FakeCoordinator:
            def rollover_to_local_date(self, day):
                events.append(("rollover", day))
            async def async_request_refresh(self):
                events.append(("network_refresh", None))
        class FakeHass:
            def async_create_task(self, coro, name):
                events.append(("schedule", name))
                self.coro = coro
        fake_hass = FakeHass()
        fake_date = date(2026, 10, 15)
        scope = {
            "hass":fake_hass,
            "coordinator":FakeCoordinator(),
            "dt_util":SimpleNamespace(now=lambda:SimpleNamespace(date=lambda:fake_date)),
        }
        exec(compile(mod, str(source), "exec"), scope)
        scope["_handle_local_midnight"](None)
        self.assertEqual(events[0], ("rollover", fake_date))
        self.assertEqual(events[1][0], "schedule")
        asyncio.run(fake_hass.coro)
        self.assertEqual(events[2][0], "network_refresh")

    def test_coordinator_cached_data_does_not_change_source_date(self):
        c = make_coordinator(())
        before = c.data.fetched_at
        c.rollover_to_local_date(date(2026,10,15))
        self.assertEqual(before,c.data.fetched_at)

    def test_cached_price_and_trend_remain_available_if_refresh_fails(self):
        from test_v164_numeric_sensors import sensor, period, load_sensor_class
        from types import SimpleNamespace
        price = sensor("on", "tomorrow", period({"on":Decimal("7.98")}),
                       period({"on":Decimal("8.05")}))
        price.coordinator.last_update_success = False
        self.assertTrue(price.available)
        self.assertEqual(price.native_value, 8.05)
        trend_source = COMPONENT / "binary_sensor.py"
        tree = ast.parse(trend_source.read_text(encoding="utf-8"))
        orig = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FuelMoreExpensiveBinarySensor")
        wanted = {"available", "_difference", "is_on"}
        methods = [node for node in orig.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
        sub = ast.ClassDef(name="MiniTrend", bases=[], keywords=[], body=methods, decorator_list=[])
        mod = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), sub], type_ignores=[])
        ast.fix_missing_locations(mod)
        scope = {"Decimal":Decimal}
        exec(compile(mod, str(trend_source), "exec"), scope)
        trend = scope["MiniTrend"]()
        trend.fuel="on"
        trend.coordinator=price.coordinator
        self.assertTrue(trend.available)
        self.assertTrue(trend.is_on)

    def test_missing_publication_is_unknown_not_stale_value_during_outage(self):
        from test_v164_numeric_sensors import sensor
        entity = sensor("on", "tomorrow", None, None)
        entity.coordinator.last_update_success = False
        self.assertTrue(entity.available)
        self.assertIsNone(entity.native_value)

    def test_refresh_started_before_midnight_cannot_overwrite_new_day(self):
        import asyncio
        source = COMPONENT / "coordinator.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FuelPriceCoordinator")
        refresh = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "_async_update_data")
        mod = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), refresh], type_ignores=[])
        ast.fix_missing_locations(mod)
        started = datetime(2026,10,14,23,59,59,tzinfo=timezone.utc)
        finished = datetime(2026,10,15,0,0,2,tzinfo=timezone.utc)
        calls = iter((started,finished))
        coord = make_coordinator(())
        target = PricePeriod(date(2026,10,15),date(2026,10,15),{"on":Decimal("8.05")})
        stale_data = FuelPriceData(date(2026,10,14), date(2026,10,15),None,target,started,1,(target,))
        class Api:
            async def async_fetch(self, today, now):
                return stale_data
        class IR:
            @staticmethod
            def async_delete_issue(hass, domain, key):
                pass
        coord._api = Api()
        coord.hass = object()
        coord.last_error_kind = coord.last_error_message = None
        scope = {
            "dt_util":SimpleNamespace(now=lambda:next(calls)),
            "FuelPriceParseError":type("FuelPriceParseError",(Exception,),{}),
            "FuelPriceApiError":type("FuelPriceApiError",(Exception,),{}),
            "ir":IR,
            "DOMAIN":"ceny_paliw_gov_pl",
            "replace":replace,
        }
        exec(compile(mod,str(source),"exec"),scope)
        result = asyncio.run(scope["_async_update_data"](coord))
        self.assertEqual(result.today_date,date(2026,10,15))
        self.assertEqual(result.tomorrow_date,date(2026,10,16))
        self.assertEqual(result.today,target)
        self.assertIsNone(result.tomorrow)
        self.assertEqual(result.fetched_at,finished)
        self.assertEqual(coord.last_successful_update,finished)

    def test_absent_coordinator_data_does_not_raise(self):
        c = Coordinator()
        c.data = None
        self.assertFalse(c.rollover_to_local_date(date(2026,10,15)))


if __name__ == "__main__":
    unittest.main()
