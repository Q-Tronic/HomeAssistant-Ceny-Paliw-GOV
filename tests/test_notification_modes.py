"""Regression tests for per-phone notification delivery modes."""

from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "notifications.py"


def _load_manager_subset() -> type:
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    manager = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FuelPriceNotificationManager"
    )
    wanted = {
        "_daily_publication_key",
        "_source_publication_key",
        "_delivered_publications",
        "_delivered_source_publications",
        "_target_date",
        "_notified_services",
        "_is_delivered",
    }
    methods = [
        node
        for node in manager.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted
    ]
    mini = ast.ClassDef(
        name="MiniManager",
        bases=[],
        keywords=[],
        body=methods,
        decorator_list=[],
    )
    module = ast.Module(body=[mini], type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {
        "Mapping": __import__("collections.abc", fromlist=["Mapping"]).Mapping,
        "FUELS": ("pb95", "pb98", "on"),
        "DEVICE_NOTIFICATION_MODE": "notification_mode",
        "PHONE_NOTIFICATION_MODE_SCHEDULED": "scheduled",
    }

    def normalize_notification_mode(value: object) -> str:
        text = str(value or "scheduled")
        return text if text in {"scheduled", "publication", "publication_change"} else "scheduled"

    namespace["normalize_notification_mode"] = normalize_notification_mode
    exec(compile(module, str(MODULE), "exec"), namespace)
    return namespace["MiniManager"]


class NotificationModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.Manager = _load_manager_subset()

    @staticmethod
    def _period() -> SimpleNamespace:
        return SimpleNamespace(
            valid_from=date(2026, 10, 10),
            valid_to=date(2026, 10, 12),
            published_on=date(2026, 10, 9),
            prices={
                "pb95": Decimal("6.97"),
                "pb98": Decimal("7.85"),
                "on": Decimal("8.06"),
            },
            source_url="https://www.gov.pl/web/energia/weekend",
        )

    def _manager(self, tomorrow_date: date, state: dict | None = None):
        manager = self.Manager()
        manager.coordinator = SimpleNamespace(
            data=SimpleNamespace(
                tomorrow_date=tomorrow_date,
                tomorrow=self._period(),
            )
        )
        manager._state = state or {}
        return manager

    def test_source_publication_key_is_stable_for_weekend_range(self) -> None:
        saturday = self._manager(date(2026, 10, 10))
        sunday = self._manager(date(2026, 10, 11))
        self.assertEqual(
            saturday._source_publication_key(),
            sunday._source_publication_key(),
        )
        self.assertNotEqual(
            saturday._daily_publication_key(),
            sunday._daily_publication_key(),
        )

    def test_publication_mode_treats_legacy_weekend_delivery_as_delivered(self) -> None:
        saturday = self._manager(date(2026, 10, 10))
        legacy_daily_key = saturday._daily_publication_key()
        sunday = self._manager(
            date(2026, 10, 11),
            {"delivered_publications": {"notify.mobile_app_robert": legacy_daily_key}},
        )
        self.assertTrue(
            sunday._is_delivered(
                "notify.mobile_app_robert",
                {"notification_mode": "publication"},
            )
        )

    def test_scheduled_mode_keeps_daily_weekend_delivery(self) -> None:
        saturday = self._manager(date(2026, 10, 10))
        saturday_key = saturday._daily_publication_key()
        sunday = self._manager(
            date(2026, 10, 11),
            {"delivered_publications": {"notify.mobile_app_robert": saturday_key}},
        )
        self.assertFalse(
            sunday._is_delivered(
                "notify.mobile_app_robert",
                {"notification_mode": "scheduled"},
            )
        )

    def test_publication_mode_uses_source_delivery_key(self) -> None:
        manager = self._manager(date(2026, 10, 10))
        source_key = manager._source_publication_key()
        manager._state = {
            "delivered_source_publications": {
                "notify.mobile_app_robert": source_key,
            }
        }
        self.assertTrue(
            manager._is_delivered(
                "notify.mobile_app_robert",
                {"notification_mode": "publication_change"},
            )
        )


if __name__ == "__main__":
    unittest.main()
