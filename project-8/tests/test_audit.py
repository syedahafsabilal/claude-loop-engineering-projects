import unittest

from dep_audit.audit import audit, read_manifest, read_registry
from tests.util import PROJECT_ROOT, base_config


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.cfg = base_config()
        self.manifest = read_manifest(self.cfg.target_dir / "manifest.json")
        self.registry = read_registry(self.cfg.registry_path)

    def test_findings_without_allow_major(self):
        findings = audit(self.manifest, self.registry, allow_major=False)
        by_name = {f.dependency: f for f in findings}
        self.assertIn("left-pad", by_name)
        self.assertIn("lodash", by_name)
        self.assertIn("express", by_name)
        # left-pad: minor, actionable
        self.assertEqual(by_name["left-pad"].bump, "minor")
        self.assertTrue(by_name["left-pad"].actionable)
        # lodash: patch + advisory, actionable
        self.assertEqual(by_name["lodash"].bump, "patch")
        self.assertTrue(by_name["lodash"].actionable)
        self.assertEqual(by_name["lodash"].advisory, "CVE-2020-8203")
        # express: major + advisory, NOT actionable by default
        self.assertEqual(by_name["express"].bump, "major")
        self.assertFalse(by_name["express"].actionable)
        # good-dep up to date -> no finding
        self.assertNotIn("good-dep", by_name)

    def test_allow_major_makes_express_actionable(self):
        findings = audit(self.manifest, self.registry, allow_major=True)
        by_name = {f.dependency: f for f in findings}
        self.assertTrue(by_name["express"].actionable)
        self.assertEqual(by_name["express"].target, "4.18.2")

    def test_actionable_count(self):
        findings = audit(self.manifest, self.registry, allow_major=False)
        self.assertEqual(len([f for f in findings if f.actionable]), 2)


if __name__ == "__main__":
    unittest.main()
