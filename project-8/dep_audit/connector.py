"""CONNECTOR stage.

Reports loop results and (optionally) opens a pull request. Credentials are
never stored in source control -- the GitHub token is read from an environment
variable at runtime. A dry-run mode ensures the project can be exercised safely
without ever touching a remote.
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from .config import LoopConfig


@dataclass
class ConnectorResult:
    pushed: bool = False
    created_pr: bool = False
    url: Optional[str] = None
    dry_run: bool = True
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class Connector(ABC):
    def __init__(self, config: LoopConfig):
        self.config = config

    @abstractmethod
    def report(self, summary: dict, worktree) -> ConnectorResult:  # pragma: no cover
        ...


class FakeConnector(Connector):
    """Deterministic connector for tests and dry-run. Records intent only."""

    def __init__(self, config: LoopConfig):
        super().__init__(config)
        self.calls: List[dict] = []
        self.pushed = False
        self.created_pr = False

    def report(self, summary: dict, worktree) -> ConnectorResult:
        res = ConnectorResult(dry_run=self.config.dry_run)
        self.calls.append(summary)
        if self.config.dry_run:
            res.notes.append("dry-run: no remote action taken")
            return res
        # Even in non-dry mode, the FakeConnector does not touch a network; it
        # simply records that it *would* have pushed / opened a PR.
        self.pushed = True
        self.created_pr = True
        res.pushed = True
        res.created_pr = True
        res.url = "https://example.invalid/pull/0"
        res.notes.append("fake connector recorded a (simulated) push + PR")
        return res


class GitHubConnector(Connector):
    """Real GitHub integration via the ``gh`` CLI.

    Safety: in dry-run mode it performs NO remote action. When not dry-run it
    pushes the worktree branch and opens a PR *only if* a token is available
    and the repo is configured. Any missing precondition fails closed (raises)
    instead of silently skipping.
    """

    def report(self, summary: dict, worktree) -> ConnectorResult:
        res = ConnectorResult(dry_run=self.config.dry_run)

        if self.config.dry_run:
            res.notes.append("dry-run: would push branch and open PR (skipped)")
            return res

        if not self.config.github_repo:
            raise RuntimeError("github_repo must be configured for real PRs")
        if not self.config.github_token:
            raise RuntimeError(
                f"no token in env var {self.config.github_token_env!r}; refusing to push"
            )
        if not getattr(worktree, "is_git", False):
            raise RuntimeError("worktree is not a git worktree; cannot push branch")

        branch = getattr(worktree, "_branch", None)
        if not branch:
            raise RuntimeError("worktree branch unknown; cannot push")

        # Push the branch.
        push = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=str(worktree.path), capture_output=True, text=True,
        )
        if push.returncode != 0:
            raise RuntimeError(f"git push failed: {push.stderr}")
        res.pushed = True

        # Open the PR.
        title = f"dep-audit: {summary.get('changes_count', 0)} dependency update(s)"
        body = summary.get("human_report", "") or "Automated dependency audit."
        pr = subprocess.run(
            ["gh", "pr", "create", "--repo", self.config.github_repo,
             "--title", title, "--body", body, "--head", branch],
            cwd=str(worktree.path), capture_output=True, text=True,
        )
        if pr.returncode != 0:
            raise RuntimeError(f"gh pr create failed: {pr.stderr}")
        res.created_pr = True
        # gh prints the PR URL to stdout.
        res.url = pr.stdout.strip().splitlines()[-1] if pr.stdout.strip() else None
        return res
