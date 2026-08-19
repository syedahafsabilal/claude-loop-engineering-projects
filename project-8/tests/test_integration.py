import glob
import json
import os
import unittest

from dep_audit.connector import FakeConnector
from dep_audit.spine import Spine
from tests.util import base_config


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.cfg = base_config()
        # Fresh logs dir for deterministic assertions.
        for f in glob.glob(str(self.cfg.log_dir / "*")):
            if os.path.isfile(f):
                os.remove(f)

    def test_full_run_produces_artifacts_and_no_remote(self):
        connector = FakeConnector(self.cfg)
        spine = Spine(self.cfg, connector=connector)
        result = spine.run_once(0)

        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.report_path)
        self.assertIsNotNone(result.log_path)
        self.assertTrue(os.path.exists(result.report_path))
        self.assertTrue(os.path.exists(result.log_path))

        report = open(result.report_path, encoding="utf-8").read()
        self.assertIn("PASSED", report)

        # Dry-run: connector must not have pushed / created a PR.
        self.assertFalse(connector.pushed)
        self.assertFalse(connector.created_pr)

        # The structured log records the checker result.
        log = json.loads(open(result.log_path, encoding="utf-8").read())
        self.assertTrue(log["checker_passed"])
        self.assertEqual(log["status"], "success")

        # index.log recorded the run.
        idx = (self.cfg.log_dir / "index.log").read_text(encoding="utf-8")
        self.assertIn(result.run_id, idx)


if __name__ == "__main__":
    unittest.main()
