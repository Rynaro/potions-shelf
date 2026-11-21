"""Protect required CI status delivery and publication without write bypasses."""

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]


class RequiredWorkflowTests(unittest.TestCase):
    def load_workflow(self, name):
        return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)

    def test_required_statuses_run_for_every_pr_and_merge_queue_candidate(self):
        for filename, job in (("validate-plugin.yml", "validate"), ("security-scan.yml", "verify-sources")):
            with self.subTest(filename=filename):
                workflow = self.load_workflow(filename)
                for event in ("pull_request", "merge_group"):
                    self.assertIn(event, workflow["on"])
                    self.assertFalse(workflow["on"][event])
                self.assertIn(job, workflow["jobs"])
                self.assertNotIn("if", workflow["jobs"][job])

    def test_main_verifier_has_read_only_permissions_and_no_push_step(self):
        workflow = self.load_workflow("generate-index.yml")
        self.assertEqual(workflow["permissions"]["contents"], "read")
        commands = "\n".join(step.get("run", "") for step in workflow["jobs"]["generate-index"]["steps"])
        self.assertNotIn("git push", commands)
        self.assertNotIn("git commit", commands)
        self.assertIn("cmp -s index.json", commands)


if __name__ == "__main__":
    unittest.main()
