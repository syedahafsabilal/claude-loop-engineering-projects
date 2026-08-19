"""Worktree isolation.

Every automated change happens in an isolated working directory so the main
working tree is never touched during automated work.

Two backends are provided:
  * ``CopyWorktree`` -- copies the target directory into a temp dir. Always
    available, deterministic, perfect for tests and simple unattended use.
  * ``GitWorktree`` -- uses `git worktree add` against a real git repository.
    Required when you want the maker's commit to live on a branch that a
    connector can push as a pull request.

Both expose ``.path`` and ``.cleanup()`` and are interchangeable.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path


class Worktree(ABC):
    path: Path

    @abstractmethod
    def cleanup(self) -> None:  # pragma: no cover - interface
        ...

    @property
    def is_git(self) -> bool:
        return (self.path / ".git").exists()

    def commit(self, message: str) -> Optional[str]:
        """Commit all changes if this is a git worktree. Returns commit sha or None."""
        if not self.is_git:
            return None
        subprocess.run(["git", "add", "-A"], cwd=str(self.path), check=True,
                       capture_output=True)
        # Do not fail if there is nothing to commit.
        res = subprocess.run(
            ["git", "commit", "-m", message], cwd=str(self.path),
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            if "nothing to commit" in res.stdout or "nothing to commit" in res.stderr:
                return None
            raise RuntimeError(f"git commit failed: {res.stderr}")
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.path),
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()


class CopyWorktree(Worktree):
    def __init__(self, source_dir, prefix: str = "dep-audit-"):
        src = Path(source_dir)
        if not src.exists():
            raise FileNotFoundError(f"source directory does not exist: {src}")
        self._tmp = tempfile.mkdtemp(prefix=prefix)
        self.path = Path(self._tmp)
        # Copy contents (including dotfiles) but not the source's .git history.
        for item in src.iterdir():
            dest = self.path / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


class GitWorktree(Worktree):
    def __init__(self, repo_dir, branch: str, base: str = "HEAD"):
        repo = Path(repo_dir)
        if not (repo / ".git").exists():
            raise FileNotFoundError(f"not a git repository: {repo}")
        self._repo = repo
        self._branch = branch
        self._tmp = tempfile.mkdtemp(prefix="dep-audit-git-")
        self.path = Path(self._tmp)
        res = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(self.path), base],
            cwd=str(repo), capture_output=True, text=True,
        )
        if res.returncode != 0:
            shutil.rmtree(self.path, ignore_errors=True)
            raise RuntimeError(f"git worktree add failed: {res.stderr}")

    def cleanup(self) -> None:
        # Remove the worktree (and its branch) so automated work is discarded
        # on failure.
        subprocess.run(["git", "worktree", "remove", "--force", str(self.path)],
                       cwd=str(self._repo), capture_output=True)
        subprocess.run(["git", "branch", "-D", self._branch],
                       cwd=str(self._repo), capture_output=True)
        shutil.rmtree(self.path, ignore_errors=True)


def create_worktree(backend: str, source_dir, branch: str = "dep-audit") -> Worktree:
    if backend == "git":
        return GitWorktree(source_dir, branch)
    if backend == "copy":
        return CopyWorktree(source_dir)
    raise ValueError(f"unknown worktree backend: {backend!r}")
