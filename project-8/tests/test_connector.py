import os
import types
import unittest

from dep_audit.config import LoopConfig
from dep_audit.connector import FakeConnector, GitHubConnector
from tests.util import PROJECT_ROOT


def _summary():
    return {"changes_count": 1, "human_report": "report"}


def _dummy_worktree(is_git=False, branch=None):
    return types.SimpleNamespace(is_git=is_git, _branch=branch, path="/tmp/x")


class FakeConnectorTests(unittest.TestCase):
    def test_dry_run_does_not_push(self):
        cfg = LoopConfig.defaults(PROJECT_ROOT)
        cfg.dry_run = True
        c = FakeConnector(cfg)
        res = c.report(_summary(), _dummy_worktree())
        self.assertFalse(res.pushed)
        self.assertFalse(res.created_pr)
        self.assertTrue(res.dry_run)

    def test_non_dry_simulates_push(self):
        cfg = LoopConfig.defaults(PROJECT_ROOT)
        cfg.dry_run = False
        c = FakeConnector(cfg)
        res = c.report(_summary(), _dummy_worktree())
        self.assertTrue(res.pushed)
        self.assertTrue(res.created_pr)
        self.assertFalse(res.dry_run)


class GitHubConnectorTests(unittest.TestCase):
    def test_dry_run_safe(self):
        cfg = LoopConfig.defaults(PROJECT_ROOT)
        cfg.dry_run = True
        c = GitHubConnector(cfg)
        res = c.report(_summary(), _dummy_worktree())
        self.assertFalse(res.pushed)
        self.assertFalse(res.created_pr)

    def test_non_dry_without_token_fails_closed(self):
        cfg = LoopConfig.defaults(PROJECT_ROOT)
        cfg.dry_run = False
        cfg.github_repo = "owner/name"
        os.environ.pop(cfg.github_token_env, None)
        c = GitHubConnector(cfg)
        with self.assertRaises(RuntimeError):
            c.report(_summary(), _dummy_worktree())


if __name__ == "__main__":
    unittest.main()
