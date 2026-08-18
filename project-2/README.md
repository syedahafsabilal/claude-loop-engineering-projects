# project-2

A small "fix-the-bugs" loop exercise. The goal is to start from deliberately
broken code and iteratively fix it until the test suite passes. Crucially, the
test command's pass/fail output is the **only** thing that decides when the work
is done — not the agent's own judgment.

## What this project is

This is a loop / agentic-engineering exercise:

1. **Phase 1** starts with `number_utils.py` containing functions that are
   genuinely broken, plus a test file that fails against that buggy code.
2. **Phase 2** runs a fix loop: run `python -m pytest -q`, read the failures,
   make ONE focused fix, repeat — up to a hard limit of attempts — until the
   tests pass. The pass/fail result of the test run is the sole arbiter of
   success.

## Functions in `number_utils.py`

- `is_prime(n)` — Returns `True` if `n` is a prime number, otherwise `False`.
- `dedupe_preserve_order(items)` — Returns the input list with duplicates
  removed while preserving the original order of first appearance.
- `running_total(numbers)` — Returns a list of running (cumulative) totals of
  the input numbers, e.g. `[1, 2, 3]` -> `[1, 3, 6]`.

## How to run the tests

From inside the `project-2/` directory:

```
python -m pytest -q
```

## Two-phase git history

- **Phase 1 commit** (`55b166c` — "Phase 1: failing tests (project-2)"):
  contains the deliberately broken implementation; the tests fail against it.
- **Phase 2 commit** (`7ae106b` — "Phase 2: fixes"): contains the minimal
  focused fixes (one per failing function) that make all tests pass.

## Current test status

Real output from running `python -m pytest -q` on this working tree:

```
3 passed in 0.58s
```

All tests pass.

## The loop run (Phase 2)

The fix loop operated under a hard cap of **max 6 test-run attempts**. It was
not allowed to keep guessing past that limit; if it hit 6 it would have reported
the remaining failures instead of trying more fixes.

Actual outcome: it took **4 attempts** before all tests passed — comfortably
within the cap.

Per-attempt breakdown:

- **Attempt 1** — 3 failed (`is_prime`, `dedupe_preserve_order`,
  `running_total` all broken).
- **Attempt 2** — 2 failed; fixed `is_prime` (guard changed from `n <= 2` to
  `n < 2` so that `2` is correctly recognized as prime).
- **Attempt 3** — 1 failed; fixed `dedupe_preserve_order` (replaced
  `sorted(set(items))`, which lost order, with an order-preserving loop).
- **Attempt 4** — **3 passed**; fixed `running_total` (removed the stray
  `+ 1` so the actual running total is returned).

The loop stopped because the tests **genuinely passed** on attempt 4
(`python -m pytest -q` reported `3 passed`), not because it reached the
6-attempt cap.
