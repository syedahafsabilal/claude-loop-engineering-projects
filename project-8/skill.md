# Dependency Audit — Skill

This document is the **authoritative instruction** for the automated
dependency-audit loop. The machine-readable mirror lives in
`dep_audit/skill.py` and must stay in sync with this file.

## 1. What the audit checks

For every dependency declared in the target manifest (`manifest.json`), the
audit:

1. Compares the **declared version** to the **known latest version** from the
   advisory registry (`audit_data/registry.json`).
2. Checks the **declared version** against each **security advisory** in the
   registry (a vulnerable version range, e.g. `<4.17.19`).
3. Classifies any difference as a `major`, `minor`, or `patch` bump.

Unknown dependencies (not present in the registry) are skipped — the loop never
invents data about packages it does not know.

## 2. What counts as an *actionable* finding

A finding is **actionable** (eligible for automatic remediation) when:

- a `minor` or `patch` upgrade is available, **or**
- a security advisory affects the current version **and** the safe target
  (latest) is within the **same major** version.

## 3. What changes are **allowed**

- Bump a dependency to its latest version when the bump is `minor` or `patch`.
- Bump a dependency to remediate an advisory when the target is within the same
  major version (urgent but still safe).

## 4. What changes are **forbidden**

- **Any `major`-version upgrade** unless `allow_major` is explicitly configured
  in the loop config. A major upgrade that also carries a security advisory is
  *escalated for human review*, not auto-applied.
- Upgrading a dependency when no newer version exists.
- Modifying anything other than the dependency manifest.
- Committing secrets or credentials of any kind.

## 5. Evidence the maker MUST provide

For every proposed change the maker records, and the checker independently
verifies, the following evidence:

- `dependency` — the package name.
- `old_version` and `new_version` (the safe target).
- `bump` — the computed bump type (`major`/`minor`/`patch`).
- `advisory` — the advisory id when the change remediates a security issue.
- An **independent re-audit** proving the target version is no longer
  actionable.

## 6. How the checker verifies (never trusts the maker)

The checker re-runs the audit from scratch on the modified manifest and checks:

- every evidence field is present,
- the change is actually present in the manifest,
- the bump type is recomputed (not trusted),
- no `major` bump exists unless `allow_major` is set,
- the number of changes is within `max_changes_per_run`,
- the changed dependencies are no longer actionable after the change,
- no secret-shaped content exists anywhere in the worktree.

If **any** check fails, the automated worktree is **discarded** and the
connector is **never** called. This is fail-closed behaviour.
