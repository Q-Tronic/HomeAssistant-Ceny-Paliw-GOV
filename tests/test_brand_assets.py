"""Validate bundled Home Assistant brand assets."""

from __future__ import annotations

from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "ceny_paliw_gov_pl" / "brand"
SOURCE_SVG = ROOT / "assets" / "icon.svg"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_info(path: Path) -> tuple[int, int, int]:
    """Return width, height and PNG color type from the IHDR chunk."""
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise AssertionError(f"{path} is not a PNG file")
    if data[12:16] != b"IHDR":
        raise AssertionError(f"{path} has no IHDR as the first PNG chunk")
    width, height = struct.unpack(">II", data[16:24])
    color_type = data[25]
    return width, height, color_type


class BrandAssetTests(unittest.TestCase):
    """Check the local brand assets shipped with the integration."""

    def test_icon_sizes_and_alpha(self) -> None:
        expected = {
            "icon.png": (256, 256),
            "icon@2x.png": (512, 512),
        }
        for filename, size in expected.items():
            with self.subTest(filename=filename):
                path = BRAND / filename
                self.assertTrue(path.is_file(), f"Missing brand asset: {filename}")
                width, height, color_type = _png_info(path)
                self.assertEqual((width, height), size)
                self.assertIn(color_type, {4, 6}, "Brand icon must contain alpha")

    def test_no_unsupported_svg_inside_brand_directory(self) -> None:
        self.assertFalse((BRAND / "icon.svg").exists())

    def test_editable_svg_source_is_preserved(self) -> None:
        self.assertTrue(SOURCE_SVG.is_file())
        self.assertIn("<svg", SOURCE_SVG.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
