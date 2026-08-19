"""MAKER stage.

The maker proposes (and writes) dependency version bumps inside an isolated
worktree. It does NOT verify its own work -- that is the checker's job. It DOES
record the evidence the checker will require.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .audit import Finding, actionable_findings, read_manifest
from .config import LoopConfig
from .worktree import Worktree


@dataclass
class ProposedChange:
    dependency: str
    old_version: str
    new_version: str
    bump: str
    advisory: str | None
    reason: str
    evidence: dict  # the finding facts the checker will independently verify

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class MakerResult:
    changes: List[ProposedChange] = field(default_factory=list)
    manifest_path: str = ""
    skipped_actionable: int = 0  # actionable findings left for a later run
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "changes": [c.to_dict() for c in self.changes],
            "manifest_path": self.manifest_path,
            "skipped_actionable": self.skipped_actionable,
            "notes": self.notes,
        }


def _manifest_file(worktree: Worktree) -> Path:
    # The maker only ever touches the dependency manifest file, never anything
    # else in the tree.
    return worktree.path / "manifest.json"


def make(worktree: Worktree, findings: List[Finding], config: LoopConfig) -> MakerResult:
    result = MakerResult()
    manifest_file = _manifest_file(worktree)
    if not manifest_file.exists():
        raise FileNotFoundError(f"manifest not found in worktree: {manifest_file}")

    actionable = actionable_findings(findings)
    applied = actionable[: config.max_changes_per_run]
    result.skipped_actionable = len(actionable) - len(applied)
    if result.skipped_actionable > 0:
        result.notes.append(
            f"{result.skipped_actionable} actionable finding(s) left for a later run "
            f"(max_changes_per_run={config.max_changes_per_run})"
        )

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    deps = manifest.setdefault("dependencies", {})

    for f in applied:
        old = str(deps.get(f.dependency))
        deps[f.dependency] = f.target
        result.changes.append(
            ProposedChange(
                dependency=f.dependency,
                old_version=old,
                new_version=f.target,
                bump=f.bump,
                advisory=f.advisory,
                reason=f.reason,
                evidence={
                    "current": f.current,
                    "latest": f.latest,
                    "bump": f.bump,
                    "advisory": f.advisory,
                    "severity": f.severity,
                    "allow_major": config.allow_major,
                },
            )
        )

    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result.manifest_path = str(manifest_file)

    # In a git worktree, persist the change on its own branch so a connector
    # can turn it into a pull request. Copy worktrees have no history.
    worktree.commit(f"dep-audit: bump {len(result.changes)} dependenc(y/ies)")
    return result
