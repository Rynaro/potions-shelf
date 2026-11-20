#!/usr/bin/env python3
"""Validate one Potions Shelf catalog entry without network access."""

from __future__ import annotations

import sys
from pathlib import Path

from manifest_validation import load_manifest, validate_manifest


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate-manifest.py <manifest-file>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Error: manifest file not found: {path}", file=sys.stderr)
        return 1
    if path.suffix != ".potion":
        print("Error: active catalog manifests must use the .potion extension", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    try:
        manifest = load_manifest(path)
        errors = validate_manifest(manifest, root / "schema" / "potion-manifest.schema.json", path)
    except Exception as exc:
        print(f"Error: unable to parse manifest: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Manifest validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Valid catalog entry: {path}")
    print("Repository access and plugin code are not verified by this offline check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
