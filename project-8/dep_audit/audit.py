"""Pure dependency-audit logic.

``audit`` is intentionally side-effect free and used by BOTH the maker and the
checker so the checker can independently re-derive findings from the same
manifest + registry. This is the heart of the maker/checker separation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import version as v
from .skill import is_actionable


@dataclass
class Finding:
    dependency: str
    current: str
    latest: str
    bump: str                # major / minor / patch
    advisory: Optional[str]  # advisory id if current version is vulnerable
    severity: Optional[str]  # severity of the advisory, if any
    actionable: bool
    target: Optional[str]    # safe target version if actionable, else None
    reason: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def load_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if not isinstance(path, (dict,)) else path


def read_manifest(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_registry(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def audit(manifest: dict, registry: dict, allow_major: bool = False) -> List[Finding]:
    """Return findings for every dependency that is outdated or vulnerable.

    The function does not mutate inputs. ``actionable`` findings are the only
    ones the maker is permitted to remediate.
    """
    findings: List[Finding] = []
    deps = manifest.get("dependencies", {})
    for dep, current in deps.items():
        entry = registry.get(dep)
        if not entry:
            # Unknown dependency: nothing in our knowledge base, skip (logged
            # elsewhere). We do not invent data.
            continue
        latest = str(entry.get("latest", current))
        if v.compare_versions(current, latest) >= 0:
            continue  # already up to date

        bump = v.bump_type(current, latest)

        advisory_id = None
        severity = None
        for adv in entry.get("advisories", []):
            rng = adv.get("vulnerable")
            if rng and v.version_in_range(current, rng):
                advisory_id = adv.get("id")
                severity = adv.get("severity")
                break

        actionable = is_actionable(bump, advisory_id is not None, allow_major)
        target = latest if actionable else None

        if advisory_id:
            reason = f"security advisory {advisory_id} ({severity}) affects {current}; latest {latest}"
        else:
            reason = f"{bump} upgrade available: {current} -> {latest}"

        if not actionable:
            reason += " [BLOCKED: major upgrade requires allow_major]"

        findings.append(
            Finding(
                dependency=dep,
                current=str(current),
                latest=latest,
                bump=bump,
                advisory=advisory_id,
                severity=severity,
                actionable=actionable,
                target=target,
                reason=reason,
            )
        )
    # Sort: security advisories first, then by dependency name for stability.
    findings.sort(key=lambda f: (f.advisory is None, f.dependency))
    return findings


def actionable_findings(findings: List[Finding]) -> List[Finding]:
    return [f for f in findings if f.actionable]
