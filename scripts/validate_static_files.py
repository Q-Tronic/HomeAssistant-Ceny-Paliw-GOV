"""Validate JSON and YAML files included in the repository."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

for path in sorted(ROOT.rglob("*.json")):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:  # noqa: BLE001
        errors.append(f"JSON {path.relative_to(ROOT)}: {err}")

for pattern in ("*.yaml", "*.yml"):
    for path in sorted(ROOT.rglob(pattern)):
        if ".github/workflows" in path.as_posix():
            # Workflow YAML is still valid YAML, so validate it too.
            pass
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as err:  # noqa: BLE001
            errors.append(f"YAML {path.relative_to(ROOT)}: {err}")

if errors:
    for error in errors:
        print(f"BŁĄD: {error}")
    sys.exit(1)

print("OK: wszystkie pliki JSON i YAML są poprawne składniowo")
