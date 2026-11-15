"""Regression checks for public README structure."""

from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def _github_slug(value: str) -> str:
    """Approximate GitHub heading anchors used by this README."""
    value = value.strip().lower()
    value = re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value.replace(" ", "-"))
    return value


class ReadmeTests(unittest.TestCase):
    def test_table_of_contents_targets_existing_headings(self) -> None:
        text = README.read_text(encoding="utf-8")
        headings = {
            _github_slug(match.group(1))
            for match in re.finditer(r"^#{2,6}\s+(.+?)\s*$", text, re.MULTILINE)
        }
        targets = re.findall(r"\]\(#([^\)]+)\)", text)
        self.assertGreaterEqual(len(targets), 10)
        self.assertEqual([target for target in targets if target not in headings], [])

    def test_readme_uses_shipped_brand_icon(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn(
            'src="custom_components/ceny_paliw_gov_pl/brand/icon@2x.png"',
            text,
        )

    def test_marketplace_instructions_and_legacy_hacs_are_present(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn("## Instalacja przez Katalog społeczności (Marketplace)", text)
        self.assertIn("## Aktualizacja przez Katalog społeczności", text)
        self.assertIn("## Instalacja przez HACS w starszych wersjach HA", text)
        self.assertIn("https://github.com/Q-Tronic/HomeAssistant-Ceny-Paliw-GOV", text)
        self.assertIn("`hacs.json`", text)

    def test_only_last_three_releases_have_readme_sections(self) -> None:
        text = README.read_text(encoding="utf-8")
        releases = re.findall(r"^## Poprawki w v(\d+\.\d+\.\d+)$", text, re.MULTILINE)
        self.assertEqual(releases, ["1.6.6", "1.6.5", "1.6.4"])

    def test_internal_ci_details_are_not_documented_as_user_sections(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertNotIn("## GitHub Actions", text)
        self.assertNotIn("## Automatyczna kontrola wersji", text)


if __name__ == "__main__":
    unittest.main()
