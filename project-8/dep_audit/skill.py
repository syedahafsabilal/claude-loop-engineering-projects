"""The dependency-audit SKILL.

This module is the *machine-readable* half of the skill. The human-readable
half lives in ``skill.md`` and MUST stay consistent with the constants and
helpers here. The skill defines:

  * what the audit checks
  * what counts as an actionable finding
  * what changes are allowed / forbidden
  * what evidence the maker must provide and the checker must verify
"""

from pathlib import Path

SKILL_NAME = "dependency-audit"

# Update types that are considered "safe" automatic bumps when not a major.
SAFE_BUMP_TYPES = ("minor", "patch")

# Findings whose only remediation is a major bump are NOT auto-applied unless
# ``allow_major`` is explicitly enabled in the configuration.
FORBIDDEN_BUMP_TYPES = ("major",)


def is_actionable(bump: str, has_advisory: bool, allow_major: bool) -> bool:
    """Decide whether a finding may be auto-remediated by the maker.

    Rules (see skill.md):
      - minor / patch upgrades are always allowed (safe bumps).
      - a security advisory within the same major is allowed (safe + urgent).
      - a major upgrade is forbidden unless ``allow_major`` is set, even if a
        security advisory exists -- that case is escalated for human review.
    """
    if bump in FORBIDDEN_BUMP_TYPES:
        return allow_major
    return True


def skill_document() -> str:
    """Return the prose skill document for logging / reporting."""
    path = Path(__file__).resolve().parent.parent / "skill.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:  # pragma: no cover - defensive
        return f"<{SKILL_NAME} skill document not found at {path}>"


# A short, machine-checkable summary surfaced in reports.
SKILL_SUMMARY = {
    "name": SKILL_NAME,
    "checks": [
        "compare each declared dependency version to the known latest version",
        "check each declared version against the security advisory database",
    ],
    "actionable": [
        "a non-major (minor/patch) upgrade is available", "a security advisory affects the current version and the safe target is within the same major",
    ],
    "allowed_changes": [
        "bump a dependency to its latest version when the bump is minor or patch",
        "bump a dependency to remediate an advisory when the target is within the same major",
    ],
    "forbidden_changes": [
        "any major-version upgrade unless allow_major is explicitly configured",
        "upgrading a dependency with no available newer version",
        "modifying anything other than the dependency manifest",
        "committing secrets or credentials",
    ],
    "evidence_required": [
        "dependency name",
        "old version and new (target) version",
        "computed bump type (major/minor/patch)",
        "advisory id when the change remediates a security issue",
        "independent re-audit proving the target version is no longer actionable",
    ],
}
