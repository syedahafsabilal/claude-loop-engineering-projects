import json
import unittest

from dep_audit.audit import audit
from dep_audit.maker import make
from dep_audit.worktree import CopyWorktree
from tests.util import base_config
from dep_audit.checker import REQUIRED_EVIDENCE_KEYS


class MakerTests(unittest.TestCase):
    def setUp(self):
        self.cfg = base_config()
        self.manifest = json.loads(
            (self.cfg.target_dir / "manifest.json").read_text(encoding="utf-8")
        )
        self.registry = json.loads(
            (self.cfg.registry_path).read_text(encoding="utf-8")
        )

    def _findings(self, allow_major=False):
        return audit(self.manifest, self.registry, allow_major=allow_major)

    def test_maker_applies_actionable_changes(self):
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            result = make(wt, self._findings(), self.cfg)
            self.assertEqual(len(result.changes), 2)
            changed = {c.dependency: c.new_version for c in result.changes}
            self.assertEqual(changed["lodash"], "4.17.21")
            self.assertEqual(changed["left-pad"], "1.3.0")
            # Manifest on disk updated.
            disk = json.loads((wt.path / "manifest.json").read_text())
            self.assertEqual(disk["dependencies"]["lodash"], "4.17.21")
        finally:
            wt.cleanup()

    def test_maker_respects_max_changes_per_run(self):
        cfg = base_config(max_changes_per_run=1)
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            result = make(wt, self._findings(), cfg)
            self.assertEqual(len(result.changes), 1)
            # Security advisory sorted first.
            self.assertEqual(result.changes[0].dependency, "lodash")
            self.assertEqual(result.skipped_actionable, 1)
        finally:
            wt.cleanup()

    def test_maker_records_required_evidence(self):
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            result = make(wt, self._findings(), self.cfg)
            for c in result.changes:
                for k in REQUIRED_EVIDENCE_KEYS:
                    self.assertIn(k, c.evidence)
        finally:
            wt.cleanup()

    def test_maker_never_touches_target(self):
        original = json.loads(
            (self.cfg.target_dir / "manifest.json").read_text()
        )
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            make(wt, self._findings(), self.cfg)
        finally:
            wt.cleanup()
        after = json.loads((self.cfg.target_dir / "manifest.json").read_text())
        self.assertEqual(original, after)


if __name__ == "__main__":
    unittest.main()
