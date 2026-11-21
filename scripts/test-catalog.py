#!/usr/bin/env python3
"""Offline regression tests for the public Potions Shelf catalog workflow."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from manifest_validation import load_manifest, validate_manifest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "potion-manifest.schema.json"
GENERATOR_PATH = Path(__file__).with_name("generate-index.py")
SPEC = importlib.util.spec_from_file_location("generate_index", GENERATOR_PATH)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def manifest_text(name: str = "hello-world", repository: str | None = None) -> str:
    repository = repository or f"https://github.com/example/{name}"
    return (
        f"name: {name}\n"
        "version: 1.2.3\n"
        "description: A small example plugin\n"
        "author: Example Author\n"
        f"repository: {repository}\n"
        'reviewed_commit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n'
        "tags:\n  - example\n"
        "dependencies:\n  - name: helper-plugin\n    version: '>=1.0.0'\n"
    )


class CatalogValidationTests(unittest.TestCase):
    def validate_text(self, text: str, filename: str = "hello-world.potion") -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / filename
            path.write_text(text, encoding="utf-8")
            return validate_manifest(load_manifest(path), SCHEMA, path)

    def test_valid_bare_and_tagged_repository_urls(self) -> None:
        self.assertEqual(self.validate_text(manifest_text()), [])
        tagged = manifest_text(repository="https://github.com/example/hello-world@v1.2.3")
        self.assertEqual(self.validate_text(tagged), [])
        quoted = manifest_text().replace("description: A small example plugin", 'description: "A plugin handles today\'s commits"')
        self.assertEqual(self.validate_text(quoted), [])

    def test_rejects_paths_query_credentials_and_ambiguous_refs(self) -> None:
        for repository in (
            "https://github.com/example/hello-world/tree/main",
            "https://github.com/example/hello-world?tab=readme",
            "https://user@github.com/example/hello-world",
            "https://github.com/example/hello-world@main",
            "https://github.com/example/hello-world@v01.2.3",
        ):
            with self.subTest(repository=repository):
                self.assertTrue(self.validate_text(manifest_text(repository=repository)))

    def test_reviewed_commit_is_required_and_literal(self) -> None:
        for replacement in ("", "reviewed_commit: abc\n", 'reviewed_commit: "' + "A" * 40 + '"\n'):
            source = manifest_text().replace('reviewed_commit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n', replacement)
            self.assertTrue(self.validate_text(source))

    def test_repository_identity_is_case_sensitive_for_install_name(self) -> None:
        errors = self.validate_text(manifest_text(repository="https://github.com/example/Hello-World"))
        self.assertTrue(any("install name derived" in error for error in errors))

    def test_rejects_self_asserted_trust_and_unsupported_checksums(self) -> None:
        for field in ("verified: true\n", "checksum: sha256:" + "a" * 64 + "\n", "signature: gpg:abc\n"):
            with self.subTest(field=field[:20]):
                self.assertTrue(self.validate_text(manifest_text() + field))

    def test_rejects_duplicate_keys_nested_cli_fields_and_aliases(self) -> None:
        cases = (
            "name: hello-world\nname: hello-world\n",
            manifest_text().replace("name: hello-world\n", "metadata:\n  name: hello-world\nname: hello-world\n"),
            manifest_text() + "other: &shared value\ncopy: *shared\n",
        )
        for text in cases:
            with self.subTest(text=text[:50]):
                try:
                    errors = self.validate_text(text)
                except Exception:
                    continue
                self.assertTrue(errors)

    def test_rejects_filename_mismatch_and_wrong_yaml_types(self) -> None:
        self.assertTrue(self.validate_text(manifest_text(), filename="other.potion"))
        self.assertTrue(self.validate_text(manifest_text().replace("tags:\n  - example", "tags: example")))
        self.assertTrue(self.validate_text(manifest_text().replace("version: 1.2.3", "version: 1")))
        duplicate_dependencies = manifest_text() + "  - name: helper-plugin\n    version: '>=1.0.0'\n"
        self.assertTrue(self.validate_text(duplicate_dependencies))

    def test_rejects_symlinked_oversized_and_misplaced_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.potion"
            target.write_text(manifest_text(), encoding="utf-8")
            link = root / "hello-world.potion"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symlink"):
                load_manifest(link)
            target.write_text("x" * 65537, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "64 KiB"):
                load_manifest(target)
            with self.assertRaisesRegex(ValueError, "not found"):
                GENERATOR.generate_index(root / "missing", root / "index.json")
            plugins = root / "plugins"
            (plugins / "nested").mkdir(parents=True)
            (plugins / "nested" / "example.potion").write_text(manifest_text(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "directly inside"):
                GENERATOR.generate_index(plugins, root / "index.json")
            nested = plugins / "nested" / "example.potion"
            nested.unlink()
            (plugins / "example.yaml").write_text(manifest_text(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "extension"):
                GENERATOR.generate_index(plugins, root / "index.json")
            validator = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate-manifest.py"), str(plugins / "example.yaml")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(validator.returncode, 0)
            self.assertIn(".potion extension", validator.stderr)
            (plugins / "example.yaml").unlink()
            plugins_link = root / "plugins-link"
            plugins_link.symlink_to(plugins, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                GENERATOR.generate_index(plugins_link, root / "index.json")

    def test_index_is_valid_deterministic_and_line_searchable_without_dependency_phantoms(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugins = root / "plugins"
            plugins.mkdir()
            (plugins / "hello-world.potion").write_text(manifest_text(), encoding="utf-8")
            (plugins / "second-tool.potion").write_text(
                manifest_text("second-tool").replace("tags:\n  - example", "tags:\n  - utility"), encoding="utf-8"
            )
            index = root / "index.json"
            GENERATOR.generate_index(plugins, index)
            first = index.read_text(encoding="utf-8")
            payload = json.loads(first)
            self.assertEqual([item["name"] for item in payload["plugins"]], ["hello-world", "second-tool"])
            self.assertNotIn("dependencies", payload["plugins"][0])
            self.assertNotIn("helper-plugin", first)
            self.assertEqual(first.count('"name":'), 2)
            GENERATOR.generate_index(plugins, index)
            self.assertEqual(index.read_text(encoding="utf-8"), first)
            matched = [line for line in first.splitlines() if "utility" in line]
            names = [
                item["name"] for line in matched
                for item in payload["plugins"] if f'"name": "{item["name"]}"' in line
            ]
            self.assertEqual(names, ["second-tool"])

    def test_invalid_catalog_does_not_replace_existing_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugins = root / "plugins"
            plugins.mkdir()
            index = root / "index.json"
            index.write_text("previous\n", encoding="utf-8")
            (plugins / "hello-world.potion").write_text(manifest_text(repository="https://example.com/unsafe"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid catalog"):
                GENERATOR.generate_index(plugins, index)
            self.assertEqual(index.read_text(encoding="utf-8"), "previous\n")

    def test_default_helper_commits_entry_and_index_together_or_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shelf = root / "shelf"
            shutil.copytree(ROOT / "scripts", shelf / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "schema", shelf / "schema")
            (shelf / "plugins").mkdir()
            source = root / "plugin"
            source.mkdir()
            (source / "plugin.potions.json").write_text(json.dumps({
                "name": "hello-world", "version": "1.2.3", "description": "A useful plugin example",
                "author": "Example Author", "potions_min_version": "2.18.0",
            }))
            command = [sys.executable, str(shelf / "scripts/create-entry.py"), str(source),
                       "example/hello-world@v1.2.3", "--reviewed-commit", "a" * 40]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            entry_path = shelf / "plugins/hello-world.potion"
            self.assertTrue(entry_path.is_file())
            index_path = shelf / "index.json"
            index = json.loads(index_path.read_text())
            self.assertEqual([item["name"] for item in index["plugins"]], ["hello-world"])
            saved_index = index_path.read_bytes()
            entry_path.unlink()
            (shelf / "plugins/invalid.potion").write_text("name: invalid\n")
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("rolled back", failed.stderr)
            self.assertFalse(entry_path.exists())
            self.assertEqual(index_path.read_bytes(), saved_index)

    def test_author_helper_creates_parser_compatible_tagged_entry_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "plugin"
            output_dir = root / "plugins"
            source.mkdir()
            output_dir.mkdir()
            (source / "plugin.potions.json").write_text(
                json.dumps({
                    "name": "hello-world",
                    "version": "1.2.3",
                    "description": "A: useful plugin for today's commits",
                    "author": "Yes",
                    "potions_min_version": "2.18.0",
                }),
                encoding="utf-8",
            )
            output = output_dir / "hello-world.potion"
            helper = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "create-entry.py"), str(source),
                 "example/hello-world@v1.2.3", "--reviewed-commit", "a" * 40, "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(helper.returncode, 0, helper.stderr)
            entry = load_manifest(output)
            self.assertEqual(entry["repository"], "https://github.com/example/hello-world@v1.2.3")
            self.assertEqual(entry["description"], "A: useful plugin for today's commits")
            self.assertEqual(validate_manifest(entry, SCHEMA, output), [])
            overwrite = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "create-entry.py"), str(source),
                 "example/hello-world", "--reviewed-commit", "a" * 40, "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(overwrite.returncode, 0)
            self.assertEqual(load_manifest(output), entry)

            wrong_extension = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "create-entry.py"), str(source),
                 "example/hello-world", "--reviewed-commit", "a" * 40, "--output", str(output_dir / "hello-world.yaml")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(wrong_extension.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
