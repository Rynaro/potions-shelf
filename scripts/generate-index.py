#!/usr/bin/env python3
"""Generate the deterministic, line-searchable Potions Shelf index."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from manifest_validation import load_manifest, validate_manifest


def generate_index(plugins_dir: Path, output_file: Path, schema_path: Path | None = None) -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = schema_path or root / "schema" / "potion-manifest.schema.json"
    if plugins_dir.is_symlink():
        raise ValueError(f"plugins directory must not be a symlink: {plugins_dir}")
    if not plugins_dir.is_dir():
        raise ValueError(f"plugins directory not found: {plugins_dir}")
    manifest_files = sorted(plugins_dir.glob("*.potion"), key=lambda item: item.name)
    unsupported = sorted([*plugins_dir.glob("*.yaml"), *plugins_dir.glob("*.yml")], key=lambda item: item.name)
    misplaced = sorted(
        item for item in plugins_dir.rglob("*")
        if item.is_file() and item.suffix in {".potion", ".yaml", ".yml"} and item.parent != plugins_dir
    )
    plugins = []
    errors = [f"{path}: catalog manifests must use the .potion extension" for path in unsupported]
    errors.extend(f"{path}: manifest entries must be directly inside {plugins_dir}" for path in misplaced)
    names: dict[str, Path] = {}

    for manifest_path in manifest_files:
        try:
            manifest = load_manifest(manifest_path)
            manifest_errors = validate_manifest(manifest, schema_path, manifest_path)
            if manifest_errors:
                errors.extend(f"{manifest_path}: {error}" for error in manifest_errors)
                continue
            name = manifest["name"]
            if name in names:
                errors.append(f"{manifest_path}: duplicate plugin name {name!r} also declared by {names[name]}")
                continue
            names[name] = manifest_path
            entry = {
                "name": name,
                "version": manifest["version"],
                "description": manifest["description"],
                "author": manifest["author"],
                "repository": manifest["repository"],
                "reviewed_commit": manifest["reviewed_commit"],
            }
            for field in ("homepage", "license", "tags", "min_potions_version", "potionfile_path"):
                if field in manifest:
                    entry[field] = manifest[field]
            plugins.append(entry)
        except Exception as exc:
            errors.append(f"{manifest_path}: {exc}")

    if errors:
        raise ValueError("Invalid catalog entries:\n" + "\n".join(f"  - {error}" for error in errors))

    categories: dict[str, list[str]] = defaultdict(list)
    for plugin in plugins:
        for tag in plugin.get("tags", []):
            categories[tag].append(plugin["name"])

    # Keep each plugin object on one line. The installed Potions client uses
    # line-oriented grep to return matching names from this index.
    lines = ["{", '  "version": "1.0.0",', f'  "total_plugins": {len(plugins)},', '  "plugins": [']
    for index, plugin in enumerate(plugins):
        suffix = "," if index + 1 < len(plugins) else ""
        lines.append("    " + json.dumps(plugin, ensure_ascii=False, sort_keys=True, separators=(",", ": ")) + suffix)
    lines.extend(["  ],", '  "categories": {'])
    category_items = sorted(categories.items())
    for index, (tag, plugin_names) in enumerate(category_items):
        suffix = "," if index + 1 < len(category_items) else ""
        lines.append("    " + json.dumps(tag, ensure_ascii=False) + ": " + json.dumps(sorted(plugin_names), ensure_ascii=False) + suffix)
    lines.extend(["  }", "}"])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output_file.parent, delete=False) as temporary:
            temp_name = temporary.name
            temporary.write("\n".join(lines) + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temp_name, output_file)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: generate-index.py <plugins-dir> <output-file>", file=sys.stderr)
        return 2
    try:
        generate_index(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
