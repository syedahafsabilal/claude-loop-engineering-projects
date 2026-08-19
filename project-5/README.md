# project-5: fix-and-review

A standalone reimplementation of a "draft candidate fixes in parallel, then
review" workflow. It is meant to generalize the *idea* of a fix loop without
actually being one (see "What would make this a loop" below).

## What it does

`fix-and-review.sh` takes a list of candidate fix attempts (from
`candidates.list` by default, or a config file passed as `$1`) and for each one:

1. Creates an **isolated git worktree** (`worktrees/<candidate>`) so candidates
   never collide with each other.
2. Launches that candidate's fix script in the **background** (`&`), so all
   candidates are drafted **in parallel**.
3. Uses **`wait`** to block until every fix attempt has finished.
4. Runs a per-candidate **reviewer** (`reviewer.sh`) whose **exit code is the
   grade** — `0` = PASS, nonzero = FAIL.
5. Prints a clear **summary** table: candidate name, PASS/FAIL, and notes.

The reviewer is a *real* check: it runs the sample project's test suite
(`test_calc.py`). Any failing assertion makes Python exit nonzero, which the
reviewer propagates, which becomes a FAIL verdict.

## The sample project

`sample-project/` is a tiny toy codebase (`calc.py`) with three deliberate bugs:

| function   | bug                                   |
|------------|---------------------------------------|
| `subtract` | off-by-one (`a - b + 1`)              |
| `multiply` | adds instead of multiplies (`a + b`)  |
| `divide`   | integer division (`a // b`)           |

`test_calc.py` asserts the correct behavior of all four functions.

The three candidates in `candidates.list` are:

- `candidate-1` — fixes `subtract` only  -> FAIL (multiply, divide still broken)
- `candidate-2` — fixes all three        -> PASS
- `candidate-3` — fixes `multiply` only  -> FAIL (subtract, divide still broken)

## How to run

```bash
cd project-5
./fix-and-review.sh
# optionally point at a different candidate list:
# ./fix-and-review.sh path/to/other.list
```

You should see each worktree created, fixes launched in parallel, a `wait`,
then a reviewer pass/fail per candidate, and a final summary table.

## Run it twice, from fresh shells — it has no memory

This script deliberately keeps **no state between runs**:

- there is **no state file** it writes and reads back,
- there is **no history / memory** of previous candidates or verdicts,
- it does not consult any persistent record to decide what to do.

Each run tears down and rebuilds every worktree/branch from the committed
source in `sample-project/`, then regenerates `logs/` from scratch. The logs
are fresh *output* on every run, not input the script learns from.

To demonstrate: open two separate terminals, run `./fix-and-review.sh` in each,
and confirm the output is identical and independent. Nothing carries over.

## What would make this a loop

Right now this is a **single pass**, not a loop. Two pieces are missing, and
they are omitted **on purpose**:

1. **A heartbeat** — a timer / cron trigger (e.g. a systemd timer, `cron` job,
   or a `while sleep` loop) that re-runs `fix-and-review.sh` automatically on a
   schedule instead of you invoking it by hand.
2. **A progress file** — a file that agents write to in order to persist state
   across runs (e.g. which candidates already passed, what was tried, what
   remains). This is what would let runs *build on* previous runs.

This script has **neither** a heartbeat nor a progress file, so it is a
one-shot parallel draft-and-review, not a self-driving fix loop.

### Why this incident warns against a heartbeat without a progress file

This project already hit the exact failure mode a heartbeat would amplify.
Earlier, the cleanup step's main-worktree guard failed to match, so its
`rm -rf` fallback deleted `sample-project` itself instead of just `worktrees/`.
A human happened to be watching, caught the destroyed repo, fixed the guard,
and recreated `sample-project`. Had a heartbeat been firing that same script
on a schedule, the bug would have re-run automatically with nobody watching,
silently wiping the source repo again and again instead of failing once in
front of a person. A progress file matters here for more than state
continuity: it is a place agents could log "cleanup ran, deleted X" so a human
— or a future loop iteration — can catch a destructive action before it
compounds.
