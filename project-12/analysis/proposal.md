# Project 12 — Improvement Proposal (draft)

Generated from progress logs dated after: **2026-08-12**

> This is a DRAFT. rules/rules.md and dreaming-state.md are unchanged. No branch/PR created yet.

## Repeated failures -> proposed additions

### 1. forgot to prefix branch with `claude/`

- **Occurrence count:** 4
- **Exact run IDs:** run-001, run-003, run-007, run-010
- **Exact log dates:** 2026-08-13, 2026-08-14, 2026-08-16, 2026-08-18

**Evidence (verbatim from logs):**

  - - CORRECTION: opened branch `fix/x` instead of a `claude/` branch; had to rename.

  - - CORRECTION: branch `patch/z` was not prefixed with `claude/`; renamed to `claude/patch-z`.

  - - CORRECTION: branch `tweak/perf` lacked the `claude/` prefix; renamed.

  - - CORRECTION: branch `feat/flag` missing `claude/` prefix; renamed.

**Smallest proposed change to rules/rules.md:**

  Append a new rule to rules/rules.md:

  ### R7 — Guard: loop-created branches must begin with `claude/`
  All branches created by the Project 12 improvement loop must begin with the `claude/` prefix. Reject branch creation that does not match this prefix before any further work proceeds.

**Why this prevents the failure:** The failure 'forgot to prefix branch with `claude/`' recurred 4 time(s) across runs (run-001, run-003, run-007, run-010) on dates 2026-08-13, 2026-08-14, 2026-08-16, 2026-08-18. Adding an explicit guard at the point where the mistake is made prevents the repeated after-the-fact correction, which is exactly the pattern observed in the logs.

## Proposed deletion (exactly one)

- **Rule to delete:** R6
- **Positive usages in processed logs:** 0
- **Runs processed:** 11 (dates: 2026-08-13, 2026-08-14, 2026-08-15, 2026-08-16, 2026-08-17, 2026-08-18, 2026-08-19)
- **Reason it is safe to delete:** Rule R6 is flagged DEPRECATED in rules/rules.md and had 0 positive usages across the 11 processed runs (dates: 2026-08-13, 2026-08-14, 2026-08-15, 2026-08-16, 2026-08-17, 2026-08-18, 2026-08-19). The debug workflow that motivated it was removed, so no recent run depends on it. Deleting it reduces noise without changing behaviour.

> The rule is NOT deleted here. It changes only if the PR is manually merged.
