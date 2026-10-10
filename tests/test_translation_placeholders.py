"""Regression tests for config/options translation placeholders."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"
TRANSLATION_FILES = (
    COMPONENT / "strings.json",
    COMPONENT / "translations" / "en.json",
    COMPONENT / "translations" / "pl.json",
)


class TranslationPlaceholderTests(unittest.TestCase):
    def test_step_titles_do_not_use_runtime_placeholders(self) -> None:
        """Step titles cannot consume description_placeholders from flow results."""
        for path in TRANSLATION_FILES:
            data = json.loads(path.read_text(encoding="utf-8"))
            for section in ("config", "options"):
                for step_id, step in data.get(section, {}).get("step", {}).items():
                    title = str(step.get("title", ""))
                    with self.subTest(file=path.name, section=section, step=step_id):
                        self.assertNotIn("{", title)
                        self.assertNotIn("}", title)

    def test_phone_name_is_kept_in_description(self) -> None:
        """Phone name remains visible through supported description placeholders."""
        for path in TRANSLATION_FILES:
            data = json.loads(path.read_text(encoding="utf-8"))
            for step_id in ("phone_menu", "phone_settings"):
                description = data["options"]["step"][step_id]["description"]
                with self.subTest(file=path.name, step=step_id):
                    self.assertIn("{device}", description)

    def test_phone_menu_mode_placeholder_is_provided(self) -> None:
        flow_source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertIn('"mode": notification_mode', flow_source)
        for path in TRANSLATION_FILES:
            data = json.loads(path.read_text(encoding="utf-8"))
            description = data["options"]["step"]["phone_menu"]["description"]
            with self.subTest(file=path.name):
                self.assertIn("{mode}", description)


if __name__ == "__main__":
    unittest.main()
