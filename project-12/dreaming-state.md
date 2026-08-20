# Dreaming State

This file records the baseline state for the Project 12 improvement loop.
The loop reads progress logs dated strictly after `last-processed-date`.

## State

- **last-processed-date**: 2026-08-12
- **loop-version**: 0 (not yet implemented)
- **total-runs-processed**: 0

## Current Rule Index

The loop tracks which rules were exercised by recent runs so it can propose
the deletion of an unused rule. Rules live in `rules/rules.md`.

| Rule ID | Description                          | Last exercised |
|---------|--------------------------------------|----------------|
| R1      | Always run tests before committing   | (unknown)      |
| R2      | Never commit secrets or keys         | (unknown)      |
| R3      | Pin dependency versions              | (unknown)      |
| R4      | Update dreaming-state after a loop   | (unknown)      |
| R5      | Require evidence before proposals    | (unknown)      |
| R6      | DEPRECATED: log to /tmp/debug.log    | (unknown)      |

> R6 is a candidate for deletion: it references a removed debug workflow and
> is expected to be unused by recent runs.
