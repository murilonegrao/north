"""Validate the placement item bank (record 0008/T21, NFR-18).

Run from the repository root:

    uv run --with jsonschema --with pyyaml python -I schema/validate_placement.py

Checks every data/placement/items/*.yaml against schema/placement-item.schema.json, plus
rules a JSON Schema cannot express: ids unique across the bank, the id matches the skill
and band, one bank_version everywhere, passages referenced by items exist, and every skill
has at least 4 items per band (the scoring needs 70% of a band to pass it).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "placement-item.schema.json").read_text())
ITEMS_DIR = ROOT / "data" / "placement" / "items"
PREFIX = {"grammar": "gr", "vocabulary": "vo", "reading": "re", "listening": "li"}
BANDS = ("A2", "B1", "B2", "C1")
MIN_PER_BAND = 4


def check(files: list[Path]) -> list[str]:
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(SCHEMA)
    versions: set[str] = set()
    seen: Counter[str] = Counter()
    for path in files:
        doc = yaml.safe_load(path.read_text())
        problems = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        for e in problems:
            errors.append(f"{path.name}: {'/'.join(map(str, e.path))}: {e.message}")
        if problems:
            continue
        versions.add(doc["bank_version"])
        skill = doc["skill"]
        if path.stem != skill:
            errors.append(f"{path.name}: file name must be {skill}.yaml")
        passages = {p["id"] for p in doc.get("passages", [])}
        per_band: Counter[str] = Counter()
        for item in doc["items"]:
            seen[item["id"]] += 1
            expected = f"{PREFIX[skill]}-{item['band'].lower()}-"
            if not item["id"].startswith(expected):
                errors.append(f"{path.name}: {item['id']} must start with {expected}")
            if "passage" in item and item["passage"] not in passages:
                errors.append(f"{path.name}: {item['id']} refers to unknown passage {item['passage']}")
            if skill in ("reading", "listening") and "passage" not in item:
                errors.append(f"{path.name}: {item['id']} needs a passage")
            per_band[item["band"]] += 1
        for band in BANDS:
            if per_band[band] < MIN_PER_BAND:
                errors.append(f"{path.name}: {band} has {per_band[band]} items, needs {MIN_PER_BAND}")
    for item_id, n in seen.items():
        if n > 1:
            errors.append(f"id {item_id} used {n} times")
    if len(versions) > 1:
        errors.append(f"bank_version differs across files: {sorted(versions)}")
    return errors


def main() -> int:
    files = sorted(ITEMS_DIR.glob("*.yaml"))
    if not files:
        print(f"no item files in {ITEMS_DIR}")
        return 1
    errors = check(files)
    for e in errors:
        print("FAIL ", e)
    if errors:
        return 1
    total = sum(len(yaml.safe_load(f.read_text())["items"]) for f in files)
    print(f"ALL PASSED  {len(files)} files, {total} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
