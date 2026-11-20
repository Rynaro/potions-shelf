#!/usr/bin/env python3
"""Create a minimal shelf entry from a Potions plugin and its GitHub URL."""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

import yaml

from manifest_validation import (
    validate_cli_literals,
    load_manifest,
    split_repository_spec,
    validate_manifest,
    validate_repository_url,
)


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_plugin_manifest(plugin_dir: Path) -> dict:
    candidates = [plugin_dir / ".potion", plugin_dir / "plugin.potions.json"]
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix == ".json":
            with path.open(encoding="utf-8") as manifest_file:
                data = json.load(manifest_file, object_pairs_hook=reject_duplicate_json_keys)
        else:
            data = load_manifest(path)
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a manifest object")
        return data
    raise ValueError(f"No .potion or plugin.potions.json found in {plugin_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate shelf metadata from a Potions plugin scaffold."
    )
    parser.add_argument("plugin_dir", type=Path, help="Directory created by potions plugin create")
    parser.add_argument("repository", help="GitHub owner/repository, optionally followed by @v1.2.3")
    parser.add_argument("--output", type=Path, help="Override the default plugins/<name>.potion destination")
    args = parser.parse_args()

    try:
        repository_spec = args.repository
        if not repository_spec.startswith("https://"):
            repository_spec = "https://github.com/" + repository_spec
        repository_error = validate_repository_url(repository_spec)
        if repository_error:
            raise ValueError(repository_error)
        repository_url, release_tag = split_repository_spec(repository_spec)
        manifest = load_plugin_manifest(args.plugin_dir)
        name = manifest.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            raise ValueError("plugin manifest name must use lowercase letters, digits, and hyphens")
        repository_slug = repository_url.rstrip("/").rsplit("/", 1)[-1]
        if repository_slug.startswith("potions-"):
            repository_slug = repository_slug[len("potions-"):]
        if name != repository_slug:
            raise ValueError(f"plugin name must match the installed name derived from repository ({repository_slug!r})")
        required = ("version", "description", "author")
        for field in required:
            if not isinstance(manifest.get(field), str) or not manifest[field].strip():
                raise ValueError(f"plugin manifest needs a non-empty string field {field!r}")

        entry = {
            "name": name,
            "version": manifest["version"],
            "description": manifest["description"],
            "author": manifest["author"],
            "repository": repository_url + (f"@{release_tag}" if release_tag else ""),
        }
        if isinstance(manifest.get("license"), str) and manifest["license"].strip():
            entry["license"] = manifest["license"]
        output_path = args.output or Path(__file__).resolve().parent.parent / "plugins" / f"{name}.potion"
        schema_path = Path(__file__).resolve().parent.parent / "schema/potion-manifest.schema.json"
        if output_path.stem != name:
            raise ValueError(f"output filename must be {name}.potion")
        if output_path.suffix != ".potion":
            raise ValueError("output filename must use the .potion extension")

        lines = []
        for field, value in entry.items():
            if not isinstance(value, str) or value != value.strip() or any(ord(char) < 32 for char in value):
                raise ValueError(f"{field} must be a single-line string without surrounding whitespace")
            try:
                plain_value = yaml.safe_load(f"{field}: {value}\n")[field]
            except (yaml.YAMLError, TypeError, KeyError):
                plain_value = None
            if plain_value == value and isinstance(plain_value, str) and not value.endswith(("'", '\"')):
                scalar = value
            elif '\"' not in value and "\\" not in value:
                scalar = f'"{value}"'
            elif "'" not in value and "\\" not in value:
                scalar = f"'{value}'"
            else:
                raise ValueError(
                    f"{field} contains quote or backslash characters the current Potions reader cannot preserve"
                )
            lines.append(f"{field}: {scalar}\n")
        manifest_text = "".join(lines)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=output_path.parent, delete=False
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(manifest_text)
            parsed_entry = load_manifest(temporary_path)
            if parsed_entry != entry:
                raise ValueError("generated YAML values do not match the Potions plugin metadata")
            errors = validate_manifest(parsed_entry, schema_path)
            if errors:
                raise ValueError("generated catalog entry is invalid: " + "; ".join(errors))
            literal_errors = validate_cli_literals(temporary_path, parsed_entry)
            if literal_errors:
                raise ValueError("generated entry is incompatible with Potions: " + "; ".join(literal_errors))
            try:
                with output_path.open("x", encoding="utf-8") as output_file:
                    output_file.write(manifest_text)
            except FileExistsError as error:
                raise ValueError(f"refusing to overwrite existing file {output_path}") from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        print(f"Created {output_path}")
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
