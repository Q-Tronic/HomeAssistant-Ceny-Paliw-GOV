"""Regression tests: missing mobile_app Repairs must wait until HA is running."""

from __future__ import annotations

import ast
import asyncio
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "notifications.py"


class CoreState(Enum):
    starting = "STARTING"
    running = "RUNNING"


class FakeBus:
    def __init__(self) -> None:
        self.listeners: dict[str, list] = {}

    def async_listen(self, name, listener):
        self.listeners.setdefault(name, []).append(listener)

        def unsubscribe():
            self.listeners[name].remove(listener)

        return unsubscribe

    def async_listen_once(self, name, listener):
        def once(event):
            unsubscribe()
            listener(event)

        unsubscribe = self.async_listen(name, once)
        return unsubscribe

    def fire(self, name, data=None):
        for listener in list(self.listeners.get(name, [])):
            listener(SimpleNamespace(data=data or {}))


class FakeHass:
    def __init__(self, state=CoreState.starting) -> None:
        self.state = state
        self.bus = FakeBus()
        self.available: set[str] = set()
        self.services = SimpleNamespace(
            has_service=lambda domain, service: (
                domain == "notify" and service in self.available
            )
        )
        self.tasks: list[asyncio.Task] = []

    def async_create_task(self, coro, _name):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task


class FakeIssueRegistry:
    IssueSeverity = SimpleNamespace(WARNING="warning")

    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []
        self.deleted: list[tuple[str, str]] = []

    def async_create_issue(self, _hass, domain, issue_id, **_kwargs):
        self.created.append((domain, issue_id))

    def async_delete_issue(self, _hass, domain, issue_id):
        self.deleted.append((domain, issue_id))


def _load_manager_subset(registry):
    source = ast.parse(MODULE.read_text(encoding="utf-8"))
    cls = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == "FuelPriceNotificationManager")
    included = {
        "async_start",
        "async_stop",
        "_target_issue_id",
        "_stored_target_issue_ids",
        "_sync_target_repairs",
        "_handle_ha_started",
        "_handle_service_registered",
    }
    methods = [
        n for n in cls.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in included
    ]
    mini = ast.ClassDef(
        name="ManagerSubset", bases=[], keywords=[], body=methods, decorator_list=[]
    )
    module = ast.Module(body=[mini], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "CoreState": CoreState,
        "callback": lambda f: f,
        "EVENT_HOMEASSISTANT_STARTED": "homeassistant_started",
        "EVENT_SERVICE_REGISTERED": "service_registered",
        "DEVICE_ENABLED": "enabled",
        "DEVICE_NAME": "name",
        "DEVICE_SERVICE": "service",
        "DOMAIN": "ceny_paliw_gov_pl",
        "SIGNAL_NOTIFICATION_STATE_UPDATED": "signal",
        "default_device_name": lambda target: target,
        "ir": registry,
        "async_dispatcher_send": lambda *args: None,
    }
    exec(compile(module, str(MODULE), "exec"), namespace)
    return namespace["ManagerSubset"]


class RepairStartupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.registry = FakeIssueRegistry()
        self.Manager = _load_manager_subset(self.registry)
        self.hass = FakeHass()
        self.manager = self.Manager()
        self.manager.hass = self.hass
        self.manager._state = {}
        self.manager.devices = [
            {"service": "notify.mobile_app_phone_a", "name": "A", "enabled": True},
            {"service": "notify.mobile_app_phone_b", "name": "B", "enabled": True},
            {"service": "notify.mobile_app_off", "name": "off", "enabled": False},
        ]
        self.saved = []

        async def save():
            self.saved.append(dict(self.manager._state))

        async def do_nothing():
            pass

        self.manager._store = SimpleNamespace(async_load=do_nothing)
        self.manager._async_save_state = save
        self.manager._prune_removed_targets_from_state = lambda: None
        self.manager.async_reschedule = do_nothing
        self.manager._async_evaluate_current_day = do_nothing
        self.manager._cancel_time_listeners = lambda: None
        self.manager.coordinator = SimpleNamespace(async_add_listener=lambda f: lambda: None)
        self.manager._unsub_ha_started = None
        self.manager._unsub_service_registered = None
        self.manager._unsub_coordinator = None
        self.manager._handle_coordinator_update = lambda: None

    async def _drain(self):
        if self.hass.tasks:
            await asyncio.gather(*self.hass.tasks)

    async def test_early_start_and_updates_do_not_create_repairs(self):
        await self.manager.async_start()
        self.manager._sync_target_repairs()  # Same function called on coordinator update.
        self.assertEqual(self.registry.created, [])
        self.assertNotIn("target_issue_ids", self.manager._state)
        self.assertEqual(len(self.hass.bus.listeners["homeassistant_started"]), 1)
        self.assertEqual(len(self.hass.bus.listeners["service_registered"]), 1)

    async def test_started_event_checks_missing_enabled_targets(self):
        await self.manager.async_start()
        self.hass.state = CoreState.running
        self.hass.bus.fire("homeassistant_started")
        await self._drain()
        self.assertEqual(len(self.registry.created), 2)
        self.assertEqual(len(self.manager._state["target_issue_ids"]), 3)
        self.assertGreaterEqual(len(self.saved), 2)
        self.assertEqual(self.hass.bus.listeners["homeassistant_started"], [])

    async def test_mobile_app_services_available_at_start_do_not_raise(self):
        await self.manager.async_start()
        self.hass.available.update({"mobile_app_phone_a", "mobile_app_phone_b"})
        self.hass.bus.fire(
            "service_registered", {"domain": "notify", "service": "mobile_app_phone_a"}
        )
        self.assertEqual(self.registry.created, [])
        self.hass.state = CoreState.running
        self.hass.bus.fire("homeassistant_started")
        await self._drain()
        self.assertEqual(self.registry.created, [])

    async def test_late_registration_clears_warning_immediately(self):
        await self.manager.async_start()
        self.hass.state = CoreState.running
        self.hass.bus.fire("homeassistant_started")
        await self._drain()
        self.hass.available.add("mobile_app_phone_a")
        before = len(self.registry.deleted)
        self.hass.bus.fire("service_registered", {"domain": "sensor", "service": "mobile_app_phone_a"})
        self.hass.bus.fire("service_registered", {"domain": "notify", "service": "unrelated"})
        self.assertEqual(len(self.registry.deleted), before)
        self.hass.bus.fire("service_registered", {"domain": "notify", "service": "mobile_app_phone_a"})
        self.assertIn(
            ("ceny_paliw_gov_pl", "missing_notify_target_notify_mobile_app_phone_a"),
            self.registry.deleted,
        )

    async def test_already_running_setup_reconciles_without_start_listener(self):
        self.hass.state = CoreState.running
        self.hass.available.add("mobile_app_phone_a")
        await self.manager.async_start()
        self.assertEqual(len(self.registry.created), 1)
        self.assertNotIn("homeassistant_started", self.hass.bus.listeners)

    async def test_stop_unsubscribes_both_event_listeners(self):
        await self.manager.async_start()
        await self.manager.async_stop()
        self.assertEqual(self.hass.bus.listeners["homeassistant_started"], [])
        self.assertEqual(self.hass.bus.listeners["service_registered"], [])
        self.hass.state = CoreState.running
        self.hass.bus.fire("homeassistant_started")
        self.hass.bus.fire("service_registered", {"domain": "notify", "service": "mobile_app_phone_a"})
        self.assertEqual(self.registry.created, [])


if __name__ == "__main__":
    unittest.main()
