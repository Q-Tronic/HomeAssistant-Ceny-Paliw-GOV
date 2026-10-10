"""Validate that repository version declarations are synchronized."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "ceny_paliw_gov_pl"


def fail(message: str) -> None:
    print(f"BŁĄD: {message}")
    raise SystemExit(1)


manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
manifest_version = str(manifest.get("version", "")).strip()
if not re.fullmatch(r"\d+\.\d+\.\d+", manifest_version):
    fail(f"Nieprawidłowa wersja manifest.json: {manifest_version!r}")

const_text = (COMPONENT / "const.py").read_text(encoding="utf-8")
match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', const_text, re.MULTILINE)
if match is None:
    fail("Nie znaleziono VERSION w const.py")
const_version = match.group(1)
if const_version != manifest_version:
    fail(
        "Wersje są różne: "
        f"manifest.json={manifest_version}, const.py={const_version}"
    )

release_file = ROOT / f"RELEASE-v{manifest_version}.md"
if not release_file.exists():
    fail(f"Brakuje pliku {release_file.name}")

changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
if (
    f"## {manifest_version}" not in changelog
    and f"## [{manifest_version}]" not in changelog
):
    fail(f"CHANGELOG.md nie zawiera sekcji wersji {manifest_version}")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
if f"v{manifest_version}" not in readme:
    fail(f"README.md nie zawiera numeru v{manifest_version}")

print(f"OK: wszystkie deklaracje wersji wskazują {manifest_version}")
sys.exit(0)
