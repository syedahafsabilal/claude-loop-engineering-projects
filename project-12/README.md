# Project 12 — Capstone Improvement Loop

A second-order improvement loop that reads a week's worth of progress logs,
detects failures/corrections that recur, and drafts the smallest possible
rules-file or skill change to prevent them — without ever modifying the
guarded rules file directly.

## Requirements

1. Read progress logs since the date recorded in `dreaming-state.md`.
2. Detect failures or corrections that appear more than once.
3. Draft the smallest rules-file or skill change to prevent a repeated failure.
4. Never directly modify the rules file as part of the automated loop.
5. Create a PR on a branch beginning with `claude/`.
6. Include evidence in the PR description:
   - exact runs/log entries supporting the proposal
   - frequency of the repeated failure
   - explanation of why the proposed change prevents it
7. Propose exactly one deletion of a rule that no recent run has needed.
8. Update `dreaming-state.md` after the loop runs.
9. Require evidence before allowing a proposal to be created.
10. Preserve a human gate: the rules file must not change unless the PR is
    manually merged.

## Layout

- `dreaming-state.md` — baseline processed date and current rule index.
- `progress-logs/` — weekly progress log inputs.
- `rules/rules.md` — guarded rules file (never edited by the loop directly).
- `analysis/` — drafted proposals and evidence (loop output).
- `tests/` — test suite (to be added).
- `loop.py` — the automated improvement loop (placeholder for now).

## Status

Scaffold only. The loop is not yet implemented.
