"""Regression tests for notification concurrency and repair cleanup."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "notifications.py"


class NotificationSafetyTests(unittest.TestCase):
    def test_automatic_delivery_is_rechecked_inside_send_lock(self) -> None:
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        manager = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "FuelPriceNotificationManager"
        )
        method = next(
            node for node in manager.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_async_send_devices"
        )
        lock_blocks = [node for node in ast.walk(method) if isinstance(node, ast.AsyncWith)]
        self.assertTrue(lock_blocks)
        lock_source = ast.unparse(lock_blocks[0])
        self.assertIn("automatic and self._is_delivered(target, device)", lock_source)

    def test_target_repair_ids_are_persisted_for_cleanup(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        self.assertIn('self._state["target_issue_ids"] = sorted(current_issue_ids)', source)
        self.assertIn('self._stored_target_issue_ids() - current_issue_ids', source)


if __name__ == "__main__":
    unittest.main()
