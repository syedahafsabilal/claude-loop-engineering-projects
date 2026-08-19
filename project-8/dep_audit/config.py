"""Configuration and budget guards for the dependency-audit loop.

All safety / budget limits live here so they can be inspected and tested in
one place. The loop is **fail-closed**: exceeding any guard stops the run.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LoopConfig:
    # --- Locations -------------------------------------------------------
    project_root: Path
    target_dir: Path
    registry_path: Path
    log_dir: Path

    # --- Worktree --------------------------------------------------------
    # "copy" (isolated directory copy) or "git" (real `git worktree add`).
    worktree_backend: str = "copy"

    # --- Budget guards ---------------------------------------------------
    max_iterations: int = 1000          # hard cap on heartbeat iterations
    max_runtime_seconds: float = 3600.0  # wall-clock cap for one `loop`
    max_changes_per_run: int = 5         # dependency bumps per single run

    # --- Safety ----------------------------------------------------------
    allow_major: bool = False           # never auto major-upgrade by default
    dry_run: bool = True                # never touch remotes unless disabled

    # --- Heartbeat -------------------------------------------------------
    interval_seconds: float = 60.0

    # --- Connector -------------------------------------------------------
    github_token_env: str = "GITHUB_TOKEN"
    github_repo: Optional[str] = None    # "owner/name"; required for real PRs

    # ---------------------------------------------------------------------

    @staticmethod
    def defaults(project_root: Path) -> "LoopConfig":
        root = Path(project_root)
        return LoopConfig(
            project_root=root,
            target_dir=root / "example_project",
            registry_path=root / "audit_data" / "registry.json",
            log_dir=root / "logs",
        )

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        for k in ("project_root", "target_dir", "registry_path", "log_dir"):
            d[k] = str(getattr(self, k))
        return d

    @classmethod
    def from_dict(cls, d: dict, project_root: Optional[Path] = None) -> "LoopConfig":
        root = Path(project_root) if project_root else Path(d.get("project_root", "."))
        return cls(
            project_root=root,
            target_dir=Path(d.get("target_dir", root / "example_project")),
            registry_path=Path(d.get("registry_path", root / "audit_data" / "registry.json")),
            log_dir=Path(d.get("log_dir", root / "logs")),
            worktree_backend=d.get("worktree_backend", "copy"),
            max_iterations=int(d.get("max_iterations", 1000)),
            max_runtime_seconds=float(d.get("max_runtime_seconds", 3600.0)),
            max_changes_per_run=int(d.get("max_changes_per_run", 5)),
            allow_major=bool(d.get("allow_major", False)),
            dry_run=bool(d.get("dry_run", True)),
            interval_seconds=float(d.get("interval_seconds", 60.0)),
            github_token_env=d.get("github_token_env", "GITHUB_TOKEN"),
            github_repo=d.get("github_repo"),
        )

    def load_from_file(self, path: Path) -> "LoopConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        merged = self.to_dict()
        merged.update(data)
        return LoopConfig.from_dict(merged, project_root=self.project_root)

    @property
    def github_token(self) -> Optional[str]:
        return os.environ.get(self.github_token_env)
