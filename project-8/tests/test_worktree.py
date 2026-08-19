import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from dep_audit.worktree import CopyWorktree, GitWorktree, create_worktree


class CopyWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.src = Path(tempfile.mkdtemp())
        (self.src / "manifest.json").write_text(
            json.dumps({"dependencies": {"a": "1.0.0"}}), encoding="utf-8"
        )

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)

    def test_copy_is_isolated(self):
        wt = CopyWorktree(self.src)
        try:
            self.assertTrue((wt.path / "manifest.json").exists())
            # Mutate the copy; original must be untouched.
            data = json.loads((wt.path / "manifest.json").read_text())
            data["dependencies"]["a"] = "9.9.9"
            (wt.path / "manifest.json").write_text(json.dumps(data))
            original = json.loads((self.src / "manifest.json").read_text())
            self.assertEqual(original["dependencies"]["a"], "1.0.0")
        finally:
            wt.cleanup()
        self.assertFalse(wt.path.exists())

    def test_create_worktree_factory(self):
        wt = create_worktree("copy", self.src)
        try:
            self.assertIsInstance(wt, CopyWorktree)
        finally:
            wt.cleanup()


class GitWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=str(self.repo), check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(self.repo), check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=str(self.repo), check=True)
        (self.repo / "manifest.json").write_text(
            json.dumps({"dependencies": {"a": "1.0.0"}}), encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=str(self.repo), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(self.repo), check=True)

    def tearDown(self):
        # Ensure any leftover worktree/branch is cleaned.
        subprocess.run(["git", "worktree", "prune"], cwd=str(self.repo), capture_output=True)
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_git_worktree_isolated_and_removable(self):
        wt = GitWorktree(self.repo, "dep-audit-test")
        try:
            self.assertTrue((wt.path / "manifest.json").exists())
            self.assertTrue(wt.is_git)
            (wt.path / "manifest.json").write_text(
                json.dumps({"dependencies": {"a": "2.0.0"}}), encoding="utf-8"
            )
            # Original repo file untouched.
            orig = json.loads((self.repo / "manifest.json").read_text())
            self.assertEqual(orig["dependencies"]["a"], "1.0.0")
        finally:
            wt.cleanup()
        self.assertFalse(wt.path.exists())
        # Branch should be gone after cleanup.
        branches = subprocess.run(["git", "branch"], cwd=str(self.repo),
                                  capture_output=True, text=True).stdout
        self.assertNotIn("dep-audit-test", branches)


if __name__ == "__main__":
    unittest.main()
