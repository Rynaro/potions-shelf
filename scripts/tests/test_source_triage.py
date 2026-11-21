import base64
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_triage
from source_triage import MAX_FILE_BYTES, MAX_FILES, scan_text, scan_tree


class SourceTriageTests(unittest.TestCase):
    def scan(self, contents, *, path="config/init.zsh", mode="100644"):
        entry = {"path": path, "type": "blob", "mode": mode, "sha": "a" * 40}
        return scan_tree([entry], lambda sha: {"content": base64.b64encode(contents).decode()})

    def test_small_shell_plugin_is_inspected_without_execution(self):
        report = self.scan(b'function hello-world() {\n  print "Hello from Potions!"\n}\n')
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["files_scanned"], 1)

    def test_sensitive_capabilities_require_triage_in_any_text_file(self):
        # These inert descriptions exercise review signals, never execution.
        for text, expected in (
            ("sudo -n true", "privilege-change"),
            ("requests.get", "network-access"),
            ("eval \"\"", "dynamic-execution"),
            ("crontab -l", "persistence"),
            ("cat ~/.ssh/config", "credential-access"),
        ):
            with self.subTest(expected=expected):
                report = self.scan(text.encode(), path="data/example.txt")
                self.assertIn(expected, {item["rule"] for item in report["findings"]})

    def test_binary_invalid_utf8_and_limits_cannot_report_clean(self):
        for content in (b"\x00", b"\xff", b"a" * (MAX_FILE_BYTES + 1)):
            with self.subTest(content_size=len(content)):
                self.assertTrue(self.scan(content)["findings"])
        report = scan_tree([{"type": "blob"}] * (MAX_FILES + 1), lambda sha: {})
        self.assertEqual(report["files_scanned"], 0)
        self.assertTrue(report["findings"])

    def test_total_budget_cannot_report_a_partial_scan_as_clean(self):
        with patch.object(source_triage, "MAX_TOTAL_BYTES", 4):
            report = self.scan(b"safe text")
        self.assertTrue(report["findings"])
        self.assertEqual(report["files_scanned"], 0)

    def test_malformed_blob_and_paths_fail_closed(self):
        for path in ("../other", "/absolute", "bad\npath"):
            report = self.scan(b"safe", path=path)
            self.assertTrue(report["findings"])
        report = scan_tree([{"path": "init.zsh", "type": "blob", "mode": "100644", "sha": "a" * 40}], lambda sha: {"content": "not base64!"})
        self.assertTrue(report["findings"])

    def test_report_contains_locations_and_advice_without_source_text(self):
        source = 'sudo quoted-secret-should-stay-out-of-report'
        report = self.scan(source.encode())
        serialized = json.dumps(report, ensure_ascii=True)
        self.assertNotIn("quoted-secret", serialized)
        self.assertIn('"line": 1', serialized)
        self.assertIn('"rule": "privilege-change"', serialized)

    def test_ordinary_documentation_and_fixed_shell_handoff_are_clean(self):
        source = "This plugin requires curl.\nUse sudo only after review.\nexec zsh\n# curl is documented here\n"
        self.assertEqual(scan_text("README.md", source), [])

    def test_full_line_comments_do_not_trigger_command_rule(self):
        self.assertEqual(scan_text("config/init.zsh", "# sudo is a documented example\nprint hello"), [])


if __name__ == "__main__":
    unittest.main()
