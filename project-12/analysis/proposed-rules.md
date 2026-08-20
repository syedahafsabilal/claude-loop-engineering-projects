# Rules

This is the guarded rules file. The Project 12 improvement loop must NEVER
edit this file directly. Any proposed change is drafted as a proposal in
`analysis/` and shipped via a PR on a `claude/` branch for manual merge.

## Rules

### R1 — Always run tests before committing
Run the test suite and confirm it passes before creating any commit.

### R2 — Never commit secrets or keys
Do not commit credentials, API keys, tokens, or other secrets to the repo.

### R3 — Pin dependency versions
Pin exact versions for all third-party dependencies.

### R4 — Update dreaming-state after a loop
After the improvement loop runs, update `dreaming-state.md` with the new
processed date.

### R5 — Require evidence before proposals
Do not create a proposal unless it is backed by concrete log evidence.

### R6 — DEPRECATED: log to /tmp/debug.log
Legacy rule: write debug output to `/tmp/debug.log`. This debug workflow
was removed; no recent run should need this rule.

### R7 — Guard: loop-created branches must begin with `claude/`
All branches created by the Project 12 improvement loop must begin with the `claude/` prefix. Reject branch creation that does not match this prefix before any further work proceeds.
