import unittest
from unittest import mock

from dep_audit.checker import CheckResult
from dep_audit.connector import FakeConnector
from dep_audit.spine import Spine
from tests.util import base_config


class SpineTests(unittest.TestCase):
    def setUp(self):
        self.cfg = base_config()

    def test_successful_run_applies_changes_and_reports(self):
        connector = FakeConnector(self.cfg)
        spine = Spine(self.cfg, connector=connector)
        result = spine.run_once(0)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.changes_count, 2)
        self.assertTrue(result.checker_passed)
        self.assertEqual(len(connector.calls), 1)

    def test_target_manifest_never_mutated(self):
        original = (self.cfg.target_dir / "manifest.json").read_text()
        spine = Spine(self.cfg, connector=FakeConnector(self.cfg))
        spine.run_once(0)
        self.assertEqual((self.cfg.target_dir / "manifest.json").read_text(), original)

    def test_failed_checker_stops_loop_and_skips_connector(self):
        connector = FakeConnector(self.cfg)
        spine = Spine(self.cfg, connector=connector)
        failing = CheckResult(passed=False, errors=["injected checker failure"])
        with mock.patch("dep_audit.spine.check", return_value=failing):
            result = spine.run_once(0)
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.checker_passed)
        # Connector must NOT have been called.
        self.assertEqual(connector.calls, [])

    def test_failed_checker_discards_worktree(self):
        spine = Spine(self.cfg, connector=FakeConnector(self.cfg))
        failing = CheckResult(passed=False, errors=["x"])
        captured = {}
        real_create = __import__("dep_audit.spine", fromlist=["create_worktree"]).create_worktree

        def spy(backend, source, branch):
            wt = real_create(backend, source, branch)
            captured["path"] = wt.path
            return wt

        with mock.patch("dep_audit.spine.create_worktree", side_effect=spy):
            with mock.patch("dep_audit.spine.check", return_value=failing):
                result = spine.run_once(0)
        self.assertEqual(result.status, "failed")
        # The worktree created for this run must have been discarded.
        self.assertIn("path", captured)
        self.assertFalse(captured["path"].exists())


if __name__ == "__main__":
    unittest.main()
