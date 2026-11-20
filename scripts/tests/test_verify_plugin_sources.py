import base64
import json
import os
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

import yaml

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importlib.util

SPEC = importlib.util.spec_from_file_location(
    "verify_plugin_sources", Path(__file__).resolve().parents[1] / "verify-plugin-sources.py"
)
verify_plugin_sources = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_plugin_sources)


COMMIT_SHA = "a" * 40
TREE_SHA = "b" * 40
BLOB_SHA = "c" * 40
TAG_SHA = "d" * 40


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code
        self.headers = {}

    def iter_content(self, chunk_size):
        yield json.dumps(self.body).encode()

    def close(self):
        pass


class FakeSession:
    def __init__(self, *, symlink=False, tagged=False, yaml_manifest=False, invalid_install_mode=False):
        self.calls = []
        self.symlink = symlink
        self.tagged = tagged
        self.yaml_manifest = yaml_manifest
        self.invalid_install_mode = invalid_install_mode

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/repos/acme/demo"):
            return FakeResponse({"private": False, "archived": False, "disabled": False, "full_name": "acme/demo", "default_branch": "main"})
        if url.endswith("/git/ref/heads/main"):
            return FakeResponse({"object": {"type": "commit", "sha": COMMIT_SHA}})
        if url.endswith("/git/ref/tags/v1.0.0"):
            return FakeResponse({"object": {"type": "tag", "sha": TAG_SHA}})
        if url.endswith(f"/git/tags/{TAG_SHA}"):
            return FakeResponse({"object": {"type": "commit", "sha": COMMIT_SHA}})
        if url.endswith(f"/git/commits/{COMMIT_SHA}"):
            return FakeResponse({"tree": {"sha": TREE_SHA}})
        if url.endswith(f"/git/trees/{TREE_SHA}"):
            manifest_path = ".potion" if self.yaml_manifest else "plugin.potions.json"
            entries = [
                {"path": manifest_path, "type": "blob", "mode": "100644", "sha": BLOB_SHA},
                {"path": "config/init.zsh", "type": "blob", "mode": "100644", "sha": BLOB_SHA},
            ]
            if self.invalid_install_mode:
                entries.append({"path": "install.sh", "type": "blob", "mode": "100644", "sha": BLOB_SHA})
            if self.symlink:
                entries.append({"path": "config/outside", "type": "blob", "mode": "120000", "sha": BLOB_SHA})
            return FakeResponse({"tree": entries, "truncated": False})
        if url.endswith(f"/git/blobs/{BLOB_SHA}"):
            manifest = {
                "name": "demo",
                "version": "1.0.0",
                "description": "A demo plugin",
                "author": "Acme",
                "potions_min_version": "2.18.0",
            }
            if self.yaml_manifest:
                content = yaml.safe_dump(manifest).encode()
            else:
                content = json.dumps(manifest).encode()
            encoded = base64.b64encode(content).decode()
            return FakeResponse({"content": encoded})
        raise AssertionError(f"Unexpected GitHub URL: {url}")


class VerifyPluginSourcesTests(unittest.TestCase):
    def run_verification(self, changed, session):
        current_directory = Path.cwd()
        try:
            os.chdir(changed.parent)
            return verify_plugin_sources.verify_changed_sources(str(changed), "", session=session)
        finally:
            os.chdir(current_directory)

    def write_catalog_manifest(self, root, repository="https://github.com/acme/demo"):
        manifest = root / "plugins" / "demo.potion"
        manifest.parent.mkdir()
        manifest.write_text(
            yaml.safe_dump(
                {
                    "name": "demo",
                    "version": "1.0.0",
                    "description": "A demo plugin",
                    "author": "Acme",
                    "repository": repository,
                }
            ),
            encoding="utf-8",
        )
        changed = root / "changed.txt"
        changed.write_text("plugins/demo.potion\n", encoding="utf-8")
        return changed

    def test_default_branch_is_resolved_and_manifest_checked_at_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = self.write_catalog_manifest(Path(directory))
            session = FakeSession()
            self.assertTrue(self.run_verification(changed, session))
            self.assertTrue(any(f"/git/commits/{COMMIT_SHA}" in url for url, _ in session.calls))
            self.assertEqual(len(session.calls), 5)

    def test_tag_uses_tag_ref_and_peels_annotated_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = self.write_catalog_manifest(Path(directory), "https://github.com/acme/demo@v1.0.0")
            session = FakeSession(tagged=True)
            self.assertTrue(self.run_verification(changed, session))
            urls = [url for url, _ in session.calls]
            self.assertIn("https://api.github.com/repos/acme/demo/git/ref/tags/v1.0.0", urls)
            self.assertNotIn("https://api.github.com/repos/acme/demo/git/ref/heads/main", urls)

    def test_yaml_manifest_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = self.write_catalog_manifest(Path(directory))
            self.assertTrue(self.run_verification(changed, FakeSession(yaml_manifest=True)))

    def test_non_executable_install_hook_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = self.write_catalog_manifest(Path(directory))
            self.assertFalse(self.run_verification(changed, FakeSession(invalid_install_mode=True)))

    def test_symlink_in_source_tree_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = self.write_catalog_manifest(Path(directory))
            self.assertFalse(
                self.run_verification(changed, FakeSession(symlink=True))
            )

    def test_catalog_identity_must_match_source_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = self.write_catalog_manifest(Path(directory))
            changed_path = Path(directory) / "plugins" / "demo.potion"
            content = yaml.safe_load(changed_path.read_text())
            content["version"] = "2.0.0"
            changed_path.write_text(yaml.safe_dump(content))
            self.assertFalse(self.run_verification(changed, FakeSession()))

    def test_deleted_manifest_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed.txt"
            changed.write_text("plugins/removed.potion\n", encoding="utf-8")
            session = FakeSession()
            self.assertTrue(self.run_verification(changed, session))
            self.assertEqual(session.calls, [])

    def test_changed_list_rejects_unsafe_filename_and_traversal(self):
        for entry in ("plugins/../escape.potion", "plugins/demo.extra.potion", "plugins/bad name.potion"):
            with self.subTest(entry=entry), tempfile.TemporaryDirectory() as directory:
                changed = Path(directory) / "changed.txt"
                changed.write_text(entry + "\n", encoding="utf-8")
                self.assertFalse(self.run_verification(changed, FakeSession()))

    def test_repository_spec_rejects_non_github_urls_and_ambiguous_paths(self):
        for value in (
            "http://github.com/acme/demo",
            "https://github.com/acme/demo/extra",
            "https://github.com/acme/demo?ref=main",
            "https://github.com/acme/demo@v1.0.0/..",
        ):
            with self.subTest(value=value), self.assertRaises(verify_plugin_sources.VerificationError):
                verify_plugin_sources.parse_repository(value)

    def test_source_yaml_aliases_and_merge_keys_are_rejected(self):
        for source in (
            b"name: demo\nbase: &defaults value\ncopy: *defaults\n",
            b"name: demo\n<<: {version: 1.0.0}\n",
        ):
            with self.subTest(source=source), self.assertRaises(verify_plugin_sources.VerificationError):
                verify_plugin_sources.load_source_yaml(source)

    def test_command_line_accepts_changed_list_and_all_active_mode(self):
        for arguments, expected_all in ((["verify-plugin-sources.py", "changed_files.txt"], False),
                                        (["verify-plugin-sources.py", "--all"], True)):
            with self.subTest(arguments=arguments), patch.object(sys, "argv", arguments), patch.object(
                verify_plugin_sources, "verify_changed_sources", return_value=True
            ) as verifier:
                self.assertEqual(verify_plugin_sources.main(), 0)
                verifier.assert_called_once()
                self.assertEqual(verifier.call_args.kwargs["all_active"], expected_all)

    def test_changed_file_script_keeps_rename_destination_and_skips_deletion(self):
        script = Path(__file__).resolve().parents[1] / "get-changed-files.sh"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            plugins = root / "plugins"
            plugins.mkdir()
            (plugins / "old-name.potion").write_text("name: old-name\n", encoding="utf-8")
            subprocess.run(["git", "add", "plugins/old-name.potion"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=root, check=True)
            subprocess.run(["git", "switch", "-c", "feature"], cwd=root, check=True, capture_output=True)

            (plugins / "old-name.potion").rename(plugins / "new-name.potion")
            (plugins / "new-name.potion").write_text("name: new-name\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "rename plugin"], cwd=root, check=True, capture_output=True)
            changed_list = root / "changed.txt"
            subprocess.run(["bash", str(script), "pull_request", "main", str(changed_list)], cwd=root, check=True, capture_output=True)
            self.assertEqual(changed_list.read_text(encoding="utf-8").splitlines(), ["plugins/new-name.potion"])

            (plugins / "new-name.potion").unlink()
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "remove plugin"], cwd=root, check=True, capture_output=True)
            subprocess.run(["bash", str(script), "pull_request", "main", str(changed_list)], cwd=root, check=True, capture_output=True)
            self.assertEqual(changed_list.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
