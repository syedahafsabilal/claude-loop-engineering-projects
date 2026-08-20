# Project-9 — One-off Scheduled Routine & Reading Runs (A1, A3, A5)

**Status: COMPLETE.** Both experiments were run and the full transcripts were
read to verify success vs. failure.

## 1. Purpose and requirements

Project-9 is a *minimal* loop-engineering exercise (difficulty: easy). The point
is **not** to build an application; it is to practice the OpenCode loop shape for
a one-off scheduled routine and to demonstrate the **A5 lesson about reading
runs**.

- Uses **A1** (loop/automation concept), **A3** (one-off schedule — no repeating
  loop), and **A5** (reading runs: the status column alone is insufficient).
- The routine performs one small, checkable task: summarize yesterday's Git
  commits onto a `claude/summary` branch.
- The exercise must **NOT** use a repeating schedule.

## 2. OpenCode was used

All runs were executed with **OpenCode** via the `opencode run` command
(headless, single-message run). The full event stream was captured with
`--format json` so the transcript — not just the exit status — could be read.

## 3. One-off shell timer, NOT a repeating schedule

OpenCode's loop here is realized with a **one-off shell timer**, not a repeating
cron/loop:

- `opencode run` runs the routine prompt exactly **once**.
- `project-9/run-oneoff.ps1` uses `Start-Sleep` for a single, fixed delay and
  then invokes one `opencode run`, writing the full transcript to
  `project-9/run-<timestamp>.txt`.

```
pwsh project-9/run-oneoff.ps1
```

This satisfies A1/A3: a one-off schedule realized with a shell timer; there is
no repeating scheduler.

## 4. The routine / task used for Run 1 (working v1)

`project-9/routine.md` (v1) instructed the agent to:

1. Determine yesterday's date range using local time.
2. Run the appropriate `git log` command to inspect yesterday's commits.
3. If there are no commits, write "No commits found for yesterday." to
   `SUMMARY.md`.
4. Create or checkout a branch named `claude/summary`.
5. Create or update `SUMMARY.md` with the summary.
6. Commit `SUMMARY.md`.
7. Report the number of commits summarized and the resulting commit hash.

## 5. Evidence from Run 1 — task actually succeeded

Transcript: **`project-9/run-20260820-170450.txt`** (session
`ses_fe0f0a487ffec6ivrUVJjQwJUb`).

Reading the full transcript confirms each required outcome:

- The agent ran
  `git log --since="2026-08-19 00:00:00" --until="2026-08-20 00:00:00"` and
  inspected **19 commits** dated **2026-08-19**.
- It ran `git checkout -b claude/summary` → `Switched to a new branch
  'claude/summary'`. The **`claude/summary`** branch was created.
- It wrote **`SUMMARY.md`** (39 lines, 19 commits summarized by project).
- It ran `git add SUMMARY.md && git commit -m "Add daily commit summary for
  2026-08-19"`, producing commit **`771f9b4`** (verified again via `git log -1
  --format=%h` → `771f9b4`).
- Final assistant message: *"**Completed!** Summarized **19 commits** from
  2026-08-19 to `SUMMARY.md` on branch `claude/summary`. **Resulting commit
  hash:** `771f9b4`"*.

## 6. The deliberately broken v2 prompt used for Run 2

`project-9/routine.md` was then replaced with v2, which **requires reading
`project-9/nonexistent-input.txt` BEFORE doing anything else**. That file was
never created, so the task is made to fail by construction: if the file cannot
be read, the agent must explicitly report failure and perform no further task
actions.

## 7. Evidence from Run 2 — task failed

Transcript: **`project-9/run-20260820-171142.txt`** (session
`ses_fe0ea5ab2ffeBlGXDgDnODuoSL`).

Reading the full transcript confirms the failure and the correct behavior:

- The very first tool call was `read` of
  `project-9/nonexistent-input.txt`, which returned
  `"status":"error"` with message
  **`File not found: ...\project-9\nonexistent-input.txt`** — the file did not
  exist.
- The agent did **not** proceed with any further task actions (no `git log`, no
  branch, no `SUMMARY.md`, no commit).
- Final assistant message: *"**Task failed.** The required input file
  `project-9/nonexistent-input.txt` does not exist. As instructed, I am not
  proceeding with any further steps (no commit summarization, no branch
  creation, no commits)."*

## 8. The A5 lesson — status column is insufficient

Crucially, **both** runs terminated with a `step_finish` reason of `"stop"` —
i.e. a **completed / green session** in the OpenCode session list. The session
status column therefore looks identical for both:

- Run 1: green session **and** the task succeeded (branch + commit `771f9b4`).
- Run 2: green session **but** the task failed (missing required file).

A5: a completed/green run status does **NOT** by itself tell you whether the
*task inside the prompt* succeeded. Only by **reading the full transcript** can
you distinguish a successful task from a failed one. The status column alone is
insufficient.

## 9. Run transcript file locations

- **Run 1 (success):** `project-9/run-20260820-170450.txt`
- **Run 2 (failure):** `project-9/run-20260820-171142.txt`

(Additional incidental `run-*.txt` files in the folder are earlier
routine-editing/setup runs, not part of the two main experiments.)

## 10. Final verification / result

The Project-9 experiment is **complete**:

- Two one-off `opencode run` sessions were executed via the shell-timer script
  (no repeating schedule).
- Run 1's full transcript proves the task succeeded: 19 commits from
  2026-08-19 summarized, `claude/summary` branch created, `SUMMARY.md` committed
  as `771f9b4`.
- Run 2's full transcript proves the task failed: `nonexistent-input.txt` was
  absent ("File not found"), the agent reported "Task failed", and performed no
  further task actions.
- Both sessions show a green/completed status, demonstrating the A5 lesson that
  the status column alone cannot distinguish a successful task from a failed one.
