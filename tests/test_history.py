"""Regression tests for local price history precedence."""

from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "history.py"


class HistorySafetyTests(unittest.TestCase):
    def test_newer_overlapping_publication_wins(self) -> None:
        source = MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        manager = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "FuelPriceHistoryManager"
        )
        record_method = next(
            node for node in manager.body
            if isinstance(node, ast.FunctionDef) and node.name == "_record_data"
        )
        rendered = ast.unparse(record_method)
        self.assertIn("reversed(tuple(periods))", rendered)

    def test_parser_resolves_newer_overlapping_publication(self) -> None:
        api_source = (ROOT / "custom_components" / "ceny_paliw_gov_pl" / "api.py").read_text(encoding="utf-8")
        tree = ast.parse(api_source)
        wanted = {"PricePeriod", "_resolve_period"}
        body = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module == "const":
                    continue
                if isinstance(node, ast.ImportFrom) and node.level:
                    continue
                body.append(node)
            elif isinstance(node, ast.ClassDef) and node.name == "PricePeriod":
                body.append(node)
            elif isinstance(node, ast.FunctionDef) and node.name == "_resolve_period":
                body.append(node)
        module = ast.Module(body=body, type_ignores=[])
        namespace: dict[str, object] = {}
        exec(compile(module, str(MODULE), "exec"), namespace)
        PricePeriod = namespace["PricePeriod"]
        resolve = namespace["_resolve_period"]
        older = PricePeriod(
            valid_from=date(2026, 10, 11), valid_to=date(2026, 10, 11),
            prices={"pb95": Decimal("6.50")}, source_url="old",
            published_on=date(2026, 10, 9),
        )
        newer = PricePeriod(
            valid_from=date(2026, 10, 11), valid_to=date(2026, 10, 11),
            prices={"pb95": Decimal("6.60")}, source_url="new",
            published_on=date(2026, 10, 10),
        )
        self.assertEqual(resolve([older, newer], date(2026, 10, 11)), newer)


if __name__ == "__main__":
    unittest.main()
