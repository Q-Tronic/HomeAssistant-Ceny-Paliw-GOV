"""Regression tests for manual actions with unsaved phone options."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"
NOTIFICATIONS = COMPONENT / "notifications.py"
CONFIG_FLOW = COMPONENT / "config_flow.py"


def _load_manual_action_methods() -> type:
    tree = ast.parse(NOTIFICATIONS.read_text(encoding="utf-8"))
    manager = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FuelPriceNotificationManager"
    )
    wanted = {"async_send_now_to_all", "async_send_now_to_target"}
    methods = [
        node
        for node in manager.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name in wanted
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
        "Any": object,
        "Mapping": __import__("collections.abc", fromlist=["Mapping"]).Mapping,
        "DEVICE_ENABLED": "enabled",
        "DEVICE_SERVICE": "service",
        "DEVICE_FUELS": "fuels",
        "DEVICE_NOTIFICATION_MODE": "notification_mode",
    }

    def normalize_fuels(value):
        return list(value or ["pb95", "pb98", "on"])

    def normalize_notification_mode(value):
        return str(value or "scheduled")

    namespace["normalize_fuels"] = normalize_fuels
    namespace["normalize_notification_mode"] = normalize_notification_mode
    exec(compile(module, str(NOTIFICATIONS), "exec"), namespace)
    return namespace["MiniManager"]


class UnsavedPhoneActionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.Manager = _load_manual_action_methods()

    def _manager(self):
        manager = self.Manager()
        manager.coordinator = SimpleNamespace(data=SimpleNamespace(tomorrow=object()))
        manager.enabled_devices = []
        manager._sync_target_repairs = lambda: None
        manager._device_map = lambda: {}
        manager.calls = []

        async def send_devices(devices, **kwargs):
            manager.calls.append((devices, kwargs))
            return len(devices)

        manager._async_send_devices = send_devices
        return manager

    async def test_unsaved_phone_can_be_sent_with_device_override(self) -> None:
        manager = self._manager()
        device = {
            "service": "notify.mobile_app_test_phone_a",
            "enabled": True,
            "fuels": ["pb95"],
            "notification_mode": "publication",
        }
        result = await manager.async_send_now_to_target(
            "notify.mobile_app_test_phone_a",
            device_override=device,
        )
        self.assertTrue(result)
        self.assertEqual(manager.calls[0][0][0]["service"], device["service"])

    async def test_send_all_override_uses_unsaved_working_devices(self) -> None:
        manager = self._manager()
        devices = [
            {"service": "notify.mobile_app_test_phone_a", "enabled": True},
            {"service": "notify.mobile_app_test_phone_b", "enabled": False},
        ]
        count = await manager.async_send_now_to_all(devices_override=devices)
        self.assertEqual(count, 1)
        self.assertEqual(
            manager.calls[0][0],
            [{"service": "notify.mobile_app_test_phone_a", "enabled": True}],
        )

    def test_options_flow_passes_working_device_to_manual_send(self) -> None:
        source = CONFIG_FLOW.read_text(encoding="utf-8")
        self.assertIn("device_override=device", source)
        self.assertIn("devices_override=list(self._existing_devices().values())", source)


if __name__ == "__main__":
    unittest.main()
