import json
import unittest
from pathlib import Path

from dep_audit.audit import audit, read_registry
from dep_audit.checker import CheckResult, check
from dep_audit.maker import MakerResult, ProposedChange
from dep_audit.worktree import CopyWorktree
from tests.util import base_config

REQUIRED = ("current", "latest", "bump", "advisory", "severity", "allow_major")


def _change(dep, old, new, bump, advisory=None, evidence=None):
    return ProposedChange(
        dependency=dep, old_version=old, new_version=new, bump=bump,
        advisory=advisory, reason="x",
        evidence=evidence or dict(current=old, latest=new, bump=bump,
                                  advisory=advisory, severity="high", allow_major=False),
    )


def _apply(wt: CopyWorktree, dep, new):
    data = json.loads((wt.path / "manifest.json").read_text())
    data["dependencies"][dep] = new
    (wt.path / "manifest.json").write_text(json.dumps(data))


class CheckerPassTests(unittest.TestCase):
    def setUp(self):
        self.cfg = base_config()
        self.registry = read_registry(self.cfg.registry_path)

    def test_checker_passes_on_valid_maker_output(self):
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            findings = audit(
                json.loads((wt.path / "manifest.json").read_text()),
                self.registry, allow_major=False,
            )
            from dep_audit.maker import make
            mr = make(wt, findings, self.cfg)
            res = check(wt, mr, self.cfg)
            self.assertTrue(res.passed, res.errors)
        finally:
            wt.cleanup()


class CheckerFailTests(unittest.TestCase):
    def setUp(self):
        self.cfg = base_config()
        self.registry = read_registry(self.cfg.registry_path)

    def test_forbidden_major_is_rejected(self):
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            _apply(wt, "express", "4.18.2")
            mr = MakerResult(changes=[_change("express", "3.0.0", "4.18.2", "major",
                                              advisory="CVE-2022-24999")])
            res = check(wt, mr, self.cfg)
            self.assertFalse(res.passed)
            self.assertTrue(any("MAJOR" in e for e in res.errors))
        finally:
            wt.cleanup()

    def test_allow_major_passes_major(self):
        cfg = base_config(allow_major=True)
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            _apply(wt, "express", "4.18.2")
            mr = MakerResult(changes=[_change("express", "3.0.0", "4.18.2", "major",
                                              advisory="CVE-2022-24999",
                                              evidence=dict(current="3.0.0", latest="4.18.2",
                                                            bump="major", advisory="CVE-2022-24999",
                                                            severity="high", allow_major=True))])
            res = check(wt, mr, cfg)
            self.assertTrue(res.passed, res.errors)
        finally:
            wt.cleanup()

    def test_secret_detection_fails(self):
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            (wt.path / ".env").write_text('password = "supersecret123"\n', encoding="utf-8")
            mr = MakerResult(changes=[])
            res = check(wt, mr, self.cfg)
            self.assertFalse(res.passed)
            self.assertTrue(res.secrets_found)
        finally:
            wt.cleanup()

    def test_over_limit_fails(self):
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            _apply(wt, "lodash", "4.17.21")
            _apply(wt, "left-pad", "1.3.0")
            mr = MakerResult(changes=[
                _change("lodash", "4.17.0", "4.17.21", "patch"),
                _change("left-pad", "1.0.0", "1.3.0", "minor"),
            ])
            cfg = base_config(max_changes_per_run=1)
            res = check(wt, mr, cfg)
            self.assertFalse(res.passed)
            self.assertTrue(any("too many changes" in e for e in res.errors))
        finally:
            wt.cleanup()

    def test_unresolved_finding_fails(self):
        wt = CopyWorktree(self.cfg.target_dir)
        try:
            # Claim left-pad was bumped but do NOT change the manifest.
            mr = MakerResult(changes=[_change("left-pad", "1.0.0", "1.3.0", "minor")])
            res = check(wt, mr, self.cfg)
            self.assertFalse(res.passed)
        finally:
            wt.cleanup()


if __name__ == "__main__":
    unittest.main()
