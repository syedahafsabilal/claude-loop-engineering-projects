import unittest
from unittest import mock

from dep_audit.config import LoopConfig
from dep_audit.connector import FakeConnector
from dep_audit.heartbeat import Heartbeat
from dep_audit.spine import Spine
from tests.util import base_config


class BudgetTests(unittest.TestCase):
    def test_max_iterations_stops_loop(self):
        cfg = base_config(max_changes_per_run=0, max_iterations=3, interval_seconds=0)
        spine = Spine(cfg, connector=FakeConnector(cfg))
        summary = Heartbeat(cfg, spine.run_once).run()
        self.assertEqual(summary.total_runs, 3)
        self.assertIn("max_iterations", summary.stop_reason)

    def test_max_runtime_stops_loop(self):
        cfg = base_config(max_changes_per_run=0, max_iterations=100,
                          max_runtime_seconds=0.5, interval_seconds=0)

        class FakeTime:
            def __init__(self):
                self.t = 0
            def monotonic(self):
                self.t += 1000.0
                return self.t
            def sleep(self, _s):
                return None

        with mock.patch("dep_audit.heartbeat.time", FakeTime()):
            spine = Spine(cfg, connector=FakeConnector(cfg))
            summary = Heartbeat(cfg, spine.run_once).run()
        self.assertIn("max_runtime_seconds", summary.stop_reason)

    def test_max_changes_per_run_enforced_in_spine(self):
        cfg = base_config(max_changes_per_run=1)
        spine = Spine(cfg, connector=FakeConnector(cfg))
        result = spine.run_once(0)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.changes_count, 1)


if __name__ == "__main__":
    unittest.main()
