# Project 8 — Unattended Dependency-Audit Loop (FINAL RECORD)

A complete, runnable **loop-engineering** capstone. It periodically inspects a
small example project's dependency manifest, finds outdated or vulnerable
dependencies, produces an audit report, and — when safe — prepares a dependency
update change in an isolated worktree. The change is independently verified
before anything is reported or turned into a pull request.

> **Status at a glance**
> - Implementation of all six loop-engineering parts: **COMPLETE**
> - Automated verification (tests + dry-run + bounded + smoke): **COMPLETE**
> - Seven-day unattended dry-run real-world validation: **IN PROGRESS** (started,
>   running in the background — see below)
>
> The code provides the *mechanism* for unattended operation. The seven-day
> real-world verification is the **only** remaining validation step and has
> **not** been completed yet.

## The problem

Dependency auditing is a boring, recurring chore: check versions, check
advisories, bump safe ones, open a PR. Doing it by hand is slow and
inconsistent. Automating it naively is dangerous — a loop that blindly upgrades
everything (including major versions) or pushes broken changes is worse than
doing nothing.

This project builds a loop that is **safe, observable, bounded, and
fail-closed**.

## Architecture

```
            +------------------- heartbeat -------------------+
            |  scheduled trigger (interval / cron / timer)    |
            +--------------------------+----------------------+
                                        |
                                        v
    target (manifest.json) --> audit --> [findings] --(if actionable)-->
                                        |
                                        v
                                 create worktree   (isolated copy / git worktree)
                                        |
                   maker ---------------+------------------------- checker
                   (propose + write)                 (independent re-audit)
                                        |
                           checker PASSED? --NO--> discard worktree, STOP
                                        |
                                        YES
                                        v
                                   connector  (report / PR; dry-run safe)
```

All six loop-engineering parts are implemented as separate, testable modules in
`dep_audit/`:

| Part | Module | Responsibility |
|------|--------|----------------|
| **Heartbeat** | `heartbeat.py` | Repeatable/scheduled trigger; enforces `max_iterations` and `max_runtime_seconds`. |
| **Worktree** | `worktree.py` | Every automated change happens in an isolated `CopyWorktree` or `GitWorktree`. Main tree never touched. |
| **Skill** | `skill.py` + `skill.md` | Defines what is checked, actionable vs forbidden, and the evidence required. |
| **Maker** | `maker.py` | Proposes safe bumps, writes the manifest, records evidence. Does **not** verify itself. |
| **Checker** | `checker.py` | Independently re-audits, validates evidence, blocks majors/over-limit/secrets. |
| **Connector** | `connector.py` | Reports results / opens PR. `FakeConnector` for tests; `GitHubConnector` for real use. Dry-run safe. |
| **Spine** | `spine.py` | Orchestrates all stages; fails closed; stops safely on any failure. |

## The six loop-engineering parts in detail

### 1. Heartbeat
`Heartbeat.run()` repeatedly calls the spine. It stops when:
- the spine reports `noop` (nothing left to do) or `failed`,
- `max_iterations` is reached, or
- `max_runtime_seconds` elapses.

Run it as `python -m dep_audit.cli loop …`. It can also be driven externally
by cron / systemd (see *Unattended scheduling*).

### 2. Worktree
`create_worktree(backend, …)` returns either a `CopyWorktree` (the target dir
is copied into a temp dir) or a `GitWorktree` (`git worktree add` against a real
git repo). The maker only ever writes `manifest.json` inside the worktree. On
checker failure the worktree is discarded.

### 3. Skill
`skill.md` is the instruction document; `skill.py` is its machine-readable
mirror (`SKILL_SUMMARY`, `is_actionable`). The skill defines:
- what the audit checks,
- what counts as actionable,
- allowed vs forbidden changes,
- the evidence the maker must provide.

### 4. Maker–Checker
The maker produces changes and records evidence; the checker **recomputes
everything** (re-audits the modified manifest, recomputes bump types, scans for
secrets) and only passes if all evidence holds. A failed check discards the
worktree and prevents the connector from running.

### 5. Connector
`GitHubConnector` opens a PR via the `gh` CLI, reading the token from the
`GITHUB_TOKEN` environment variable (never stored in source control). In
`dry_run` mode it performs **no** remote action. `FakeConnector` is a
deterministic stand-in used by the tests and as the default when no repo is
configured.

### 6. Spine
`Spine.run_once()` wires the stages in order, logs each one, and decides whether
the heartbeat should continue. Any stage error stops the run safely.

## How the loop works (one iteration)

1. **Audit** the real target manifest (read-only). If nothing actionable →
   `noop`, stop.
2. **Create** an isolated worktree.
3. **Maker** proposes safe bumps (up to `max_changes_per_run`), writes the
   manifest, records evidence.
4. **Checker** independently re-audits and validates. On failure → discard
   worktree, `failed`, stop (fail closed).
5. **Connector** reports / opens PR (respecting `dry_run`).
6. A report (`run-*.md`) and structured log (`run-*.json`) are written to
   `logs/`.

## Budget guards

All guards live in `dep_audit/config.py` (`LoopConfig`) and are overridable via
`config.json` or CLI flags:

- `max_iterations` — hard cap on loop iterations (default 1000).
- `max_runtime_seconds` — wall-clock cap for one `loop` (default 3600).
- `max_changes_per_run` — maximum dependency bumps per run (default 5).
- `allow_major` — **false** by default; major upgrades are forbidden unless set.
- `dry_run` — **true** by default; never pushes or opens PRs unless disabled.
- Fail-closed: a failed checker or connector discards the worktree and stops.

The loop **never** blindly upgrades everything, never auto-applies major
upgrades unless configured, never commits secrets, and never bypasses the
checker.

## Fail-closed behavior

The spine is fail-closed by design (`spine.py`):
- Any stage error (audit, worktree, maker, checker, connector) stops the run
  safely and is recorded in the run log.
- A **failed checker** discards the isolated worktree (no leftover changes) and
  the connector is **never** called.
- A **failed connector** (e.g. missing token / repo / `gh`) also discards the
  worktree and raises instead of silently skipping.
- The heartbeat stops the whole loop on any `failed` run or on an unexpected
  exception.

## Observability and logs

Every run writes to `logs/` (excluded from version control by `.gitignore`):
- `run-<ts>-<iter>-<id>.json` — machine-readable record (stages, timings,
  findings, changes, checker result, errors).
- `run-<ts>-<iter>-<id>.md` — human-readable report.
- `index.log` — one line per run for quick scanning.

Each stage (heartbeat, audit, worktree, maker, checker, connector) logs a
status and message, so failures are diagnosable.

## Dry-run safety

`--dry-run` (the default) means the connector performs **no** remote action. It
is the safe mode for development, CI, and the unattended validation. Logs show
`dry_run=True` and `pushed=False / created_pr=False`. Real GitHub pushing/PR
creation is **not** enabled yet.

## GitHub connector

1. Install the GitHub CLI (`gh`) and authenticate (`gh auth login`).
2. Export the token (never commit it):
   ```powershell
   $env:GITHUB_TOKEN = "ghp_..."     # or use a fine-grained PAT
   ```
3. Run with remote enabled:
   ```powershell
   python -m dep_audit.cli loop --no-dry-run --repo owner/name
   ```
   The `GitHubConnector` pushes the worktree branch and opens a PR. Missing
   token/repo/`gh` fails **closed** (raises) instead of silently skipping.

> For the current validation phase the connector is deliberately left in
> dry-run mode; no remote writes occur.

## Tests and verification

### Unit tests
`python -m unittest discover -s tests -t .` → **33 tests passed (OK)**.
Coverage includes: version logic, audit findings/actionability, worktree
isolation (copy + git), maker limits/evidence, checker pass and failure cases
(major, secret, over-limit, unresolved), spine fail-closed + worktree discard,
connector dry-run safety, and all budget guards (iterations, runtime,
per-run changes).

### Dry-run single-run verification
`python -m dep_audit.cli run --dry-run` → **passed**:
`status=success findings=3 changes=2 checker=True`. `express` is correctly
blocked as a major upgrade; `lodash` and `left-pad` are auto-bumped within safe
bounds.

### Bounded heartbeat test
`python -m dep_audit.cli loop --dry-run --max-iterations 2 --interval 0` →
**passed**: stopped with `max_iterations reached`, `runs=2`.

### Detached smoke test
Started detached with:
```powershell
Start-Process -FilePath python `
  -WorkingDirectory "C:\Users\Ali\Desktop\claude-loop-engineering-projects\project-8" `
  -ArgumentList "-m","dep_audit.cli","loop","--dry-run","--max-runtime","300","--max-iterations","10","--interval","60" `
  -RedirectStandardOutput "logs\smoke.out.log" `
  -RedirectStandardError "logs\smoke.err.log" `
  -PassThru
```
Result → **passed**: the loop ran repeatedly in the background, the **checker
passed** on every iteration, and there were **no stderr errors**
(`logs\smoke.err.log` empty; `logs\index.log` shows `status=success` /
`checker=True` for each run). The process self-terminated at its budget.

## Week-long unattended dry-run (IN PROGRESS)

The seven-day unattended validation has been **STARTED** and is **currently
running in the background**. It is a **dry-run** — no GitHub pushes or PRs are
performed.

**Command actually used to launch this validation (Windows CMD, detached /
background):**

```cmd
start "Project8Week" /B cmd /c "python -m dep_audit.cli loop --dry-run --max-runtime 604800 --max-iterations 100000 --interval 3600 > logs\week.out.log 2> logs\week.err.log"
```

This `start /B` command was the launcher **actually used** for the current
unattended run. Immediately after launch, **PID 15852** was observed running
(the loop was restarted with the same command after the missing input files
were restored; the originally-launched PID 8164 had been running against the
deleted `manifest.json`/`registry.json` and was stopped and relaunched). The
underlying loop command (also shown for reference) is:

```powershell
cd C:\Users\Ali\Desktop\claude-loop-engineering-projects\project-8
python -m dep_audit.cli loop --dry-run --max-runtime 604800 --max-iterations 100000 --interval 3600
```

At that early point:
- `logs/index.log` recorded the first current run as `status=success` with
  `checker=True`.
- `logs/week.err.log` had **no error output**.

**Active configuration for the week-long run:**
- `--dry-run` — no remote actions (no pushes, no PRs).
- `--max-runtime 604800` — 7-day wall-clock cap (the run self-terminates after
  one week).
- `--max-iterations 100000` — high enough that the 7-day runtime cap governs.
- `--interval 3600` — one audit pass per hour (~168 runs over the week).
- Inherited defaults (unchanged): `max_changes_per_run=5`,
  `allow_major=false`, `worktree_backend=copy`.

Because dry-run + copy worktree never mutates the real target, the same findings
recur each pass; the loop will not reach `noop` and relies on the budget guards
to terminate after seven days. This first long run therefore proves
**stability, consistency, and fail-closed safety under repetition** — not
progression.

### How to inspect while it runs
```powershell
# quick pass/fail per run
Get-Content "C:\Users\Ali\Desktop\claude-loop-engineering-projects\project-8\logs\index.log" -Tail 20

# latest structured run record
Get-ChildItem "C:\Users\Ali\Desktop\claude-loop-engineering-projects\project-8\logs\*.json" |
  Sort-Object LastWriteTime | Select-Object -Last 1 | ForEach-Object { Get-Content $_.FullName }

# process stdout / stderr
Get-Content "C:\Users\Ali\Desktop\claude-loop-engineering-projects\project-8\logs\week.out.log" -Tail 20
Get-Content "C:\Users\Ali\Desktop\claude-loop-engineering-projects\project-8\logs\week.err.log" -Tail 20
```

### How to stop early (if needed)
```powershell
Stop-Process -Id <PID>   # PID from the Start-Process output, or locate via:
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Select-Object ProcessId, CommandLine | Where-Object { $_.CommandLine -like "*dep_audit.cli*loop*" }
```

## Completion status — three distinct phases

| Phase | State |
|-------|-------|
| Implementation (all six parts) | **COMPLETE** |
| Automated verification (tests + dry-run + bounded + smoke) | **COMPLETE** |
| Seven-day unattended dry-run real-world validation | **IN PROGRESS** (running in background) |

The seven-day requirement is the **only** remaining real-world validation step.
It has **not** been completed; this document does **not** claim otherwise.

## Project 8 Completion Status

- [x] **Implementation of all six loop-engineering parts** (heartbeat, worktree,
      skill, maker-checker, connector, spine)
- [x] **Budget guards** implemented (`max_iterations`, `max_runtime_seconds`,
      `max_changes_per_run`, `allow_major`, `dry_run`)
- [x] **Fail-closed behavior** (checker failure discards worktree, never calls
      connector; heartbeat stops on failure)
- [x] **Observability and logs** (per-run JSON + markdown report + `index.log`)
- [x] **Dry-run safety** (default `dry_run=true`; no remote writes)
- [x] **GitHub connector** (code complete; real push/PR not enabled yet)
- [x] **Unit tests** — 33 tests passed
- [x] **Dry-run single-run verification** — passed
- [x] **Bounded heartbeat test** — passed
- [x] **Detached smoke test** — passed (checker passed every iteration; no
      stderr errors)
- [ ] **Week-long unattended dry-run** — IN PROGRESS (started, running in
      background; see configuration above)
- [ ] **Seven-day real-world validation declared COMPLETE** — NOT YET DONE

## What must be checked after seven days

Before Project 8 can be marked **FULLY COMPLETE**, review at the end of the
week:

1. `logs/index.log` — every entry is `status=success`/`noop` with
   `checker_passed=True`; **no** `status=failed`.
2. A representative `run-*.json` shows correct findings (`express` blocked as
   major; `lodash`/`left-pad` actionable) and `pushed=False` / `created_pr=False`
   — dry-run honored throughout.
3. **No real PRs or pushes** occurred on the GitHub side.
4. The target was never mutated: `example_project/manifest.json` is byte-identical
   to its starting state (CopyWorktree isolation).
5. The loop ran repeatedly and ended for the correct reason
   (`stop_reason: max_runtime_seconds reached` / `max_iterations reached`) — it
   did not die early.
6. Re-run `python -m unittest discover -s tests -t .` to confirm the
   implementation is still green.
7. Only after all of the above pass may the seven-day requirement be marked
   complete and `--no-dry-run` be considered for a future real run.

> Until step 7 is satisfied, Project 8 remains **implementation-complete and
> automated-verification-complete, but NOT fully complete**.

## How to run locally (reference)

```powershell
cd project-8
python -m dep_audit.cli run --dry-run        # single run, safe
python -m dep_audit.cli loop --dry-run       # heartbeat loop, safe
python -m dep_audit.cli run --dry-run --allow-major   # show major path handled
```

## Unattended scheduling (reference)

Two supported modes:
- **Internal heartbeat** — `python -m dep_audit.cli loop` runs, bounded by
  `max_runtime_seconds` and `max_iterations`, sleeping `interval_seconds` between
  ticks. Pair with a process supervisor (systemd, kubernetes, supervisor) for
  resilience.
- **External scheduler** — run `python -m dep_audit.cli run` from cron / systemd
  timer / Windows Task Scheduler. Each invocation is one safe pass.

Example systemd timer snippet (Linux):

```ini
# /etc/systemd/system/dep-audit.timer
[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

# /etc/systemd/system/dep-audit.service
[Service]
Type=oneshot
WorkingDirectory=/path/to/project-8
ExecStart=/usr/bin/python -m dep_audit.cli run --dry-run
```

## How to inspect failures (reference)

- Read `logs/index.log` — quick pass/fail per run.
- Open the relevant `logs/run-*.json` — full stage log, errors, checker result.
- The `failed` runs show which stage failed and why; checker failures list each
  violated rule (e.g. forbidden major, over-limit, unresolved finding, secret
  detected).
