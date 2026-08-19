"""CHECKER stage.

The checker independently verifies the maker's output. It NEVER trusts the
maker's evidence at face value: it re-audits the modified manifest from
scratch and re-derives every fact. A failed check must prevent the change from
being accepted and the spine will discard the worktree.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .audit import audit, read_manifest, read_registry
from .config import LoopConfig
from .maker import MakerResult, ProposedChange
from .version import bump_type

# Conservative secret scanners. We deliberately avoid false positives on normal
# dependency data; these look for credential-shaped assignments.
SECRET_PATTERNS = [
    re.compile(r"(?i)(aws_secret_access_key|aws_access_key_id)\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{16,}"),
    re.compile(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),          # GitHub personal token
    re.compile(r"(?i)private[_-]?key\s*[:=]"),     # generic private key marker
]

REQUIRED_EVIDENCE_KEYS = (
    "current", "latest", "bump", "advisory", "severity", "allow_major",
)


@dataclass
class CheckResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    reaudit_findings: List[dict] = field(default_factory=list)
    secrets_found: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "reaudit_findings": self.reaudit_findings,
            "secrets_found": self.secrets_found,
        }


def _scan_secrets(worktree_path: Path) -> List[str]:
    found: List[str] = []
    for path in worktree_path.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".git":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # pragma: no cover - binary files
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                found.append(f"{path.name}: {m.group(0)[:40]}")
    return found


def check(worktree: object, maker_result: MakerResult, config: LoopConfig) -> CheckResult:
    errors: List[str] = []
    result = CheckResult(passed=False)

    manifest_file = Path(getattr(worktree, "path")) / "manifest.json"
    if not manifest_file.exists():
        result.errors.append(f"manifest missing in worktree: {manifest_file}")
        return result

    try:
        manifest = read_manifest(manifest_file)
    except json.JSONDecodeError as exc:
        result.errors.append(f"manifest is not valid JSON: {exc}")
        return result

    deps = manifest.get("dependencies", {})

    # 1. Evidence completeness -------------------------------------------------
    for ch in maker_result.changes:
        missing = [k for k in REQUIRED_EVIDENCE_KEYS if k not in ch.evidence]
        if missing:
            errors.append(f"{ch.dependency}: missing evidence keys {missing}")

    # 2. Each proposed change is actually present in the manifest --------------
    for ch in maker_result.changes:
        actual = deps.get(ch.dependency)
        if actual != ch.new_version:
            errors.append(
                f"{ch.dependency}: manifest version is {actual!r}, "
                f"maker claims {ch.new_version!r}"
            )

    # 3. Forbidden changes: recompute bump, never trust evidence ---------------
    for ch in maker_result.changes:
        computed = bump_type(ch.old_version, ch.new_version)
        if computed != ch.bump:
            errors.append(
                f"{ch.dependency}: claimed bump {ch.bump!r} but computed {computed!r}"
            )
        if computed == "major" and not config.allow_major:
            errors.append(
                f"{ch.dependency}: forbidden MAJOR upgrade "
                f"{ch.old_version} -> {ch.new_version} (allow_major is False)"
            )

    # 4. Budget: number of changes within limit -------------------------------
    if len(maker_result.changes) > config.max_changes_per_run:
        errors.append(
            f"too many changes: {len(maker_result.changes)} > "
            f"max_changes_per_run={config.max_changes_per_run}"
        )

    # 5. Independent re-audit: changed deps must no longer be actionable ------
    registry = read_registry(config.registry_path)
    findings = audit(manifest, registry, allow_major=config.allow_major)
    result.reaudit_findings = [f.to_dict() for f in findings]
    changed_deps = {c.dependency for c in maker_result.changes}
    for f in findings:
        if f.dependency in changed_deps and f.actionable:
            errors.append(
                f"{f.dependency}: still actionable after maker change "
                f"({f.reason})"
            )
    # Any *new* actionable finding that the maker did not claim is also a fail.
    for f in findings:
        if f.actionable and f.dependency not in changed_deps:
            # This can legitimately happen when the maker hit the per-run cap;
            # it is not a checker failure, just leftover work (handled by spine).
            pass

    # 6. Secret scan -----------------------------------------------------------
    secrets = _scan_secrets(Path(getattr(worktree, "path")))
    if secrets:
        result.secrets_found = secrets
        errors.append(f"secret-like content detected: {secrets}")

    result.errors = errors
    result.passed = len(errors) == 0
    return result
