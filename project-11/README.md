# Project 11 — Human-Gated Two-Routine Automation Loop

## 1. Overview

Project 11 is a self-contained, **loop-engineering** exercise that builds and
actually runs a *human-gated* automation loop with two routines:

- **Routine A** — a one-off scheduled routine that produces a **reviewable**
  draft on a dedicated branch and records an explicit `pending` review state.
- **Routine B** — an **API-triggered** routine that performs one small
  follow-up action, but **only after a human explicitly approves** the draft.

The whole system runs **locally** with no cloud service, no external API, and
no fabricated calls. Everything is implemented in Python 3 standard library
(`http.server`, `json`, `secrets`, `subprocess` for git) plus `git` and
`curl`. The implementation was built **and tested**, not merely documented.

---

## 2. Original Objective

1. **Routine A (one-off):** produces something reviewable — a draft file on a
   branch plus a `review.json` artifact carrying an explicit `review_state`.
2. **Routine B (API trigger):** exposes an HTTP endpoint protected by a bearer
   token and performs one small follow-up action (applying an approval note to
   the draft and committing it).
3. **Human gate:** B must **only** run after explicit human approval. The API
   trigger alone is **not** approval.
4. **Human fires B:** after reviewing and approving, the human fires Routine B
   using the `curl` call associated with the API trigger configured in step A3.

These map directly onto the completion conditions: B ran only because its
trigger was explicitly fired; B's transcript proves the action; the A6 checklist
was run against both routines; connectors were pruned; unrestricted pushes are
disabled; a state file was explicitly chosen.

---

## 3. Architecture

```
                 +-------------------+
                 |     config.json   |  state file, push policy,
                 |                   |  connectors, B API, limits
                 +---------+---------+
                           |
              +------------+------------+
              |      loop_state.json    |  <- EXPLICITLY CHOSEN state file
              |  (iterations, deadline,|     records A/B status, A3 token state
              |   a.* , b.* , a3.*)    |
              +------------+------------+
                           |
        +------------------+------------------+
        |                  |                  |
+-------v-------+  +-------v--------+  +-------v--------+
|  Routine A    |  | Human approval |  |   Routine B    |
| (one-off)     |  | gate           |  | (API trigger)  |
| routine_a.py  |  | approve.py     |  | api_b.py       |
+-------+-------+  +-------+--------+  +-------+--------+
        |                  |                  |
        |  creates draft   | sets approved    | POST /trigger
        |  (branch+pending)| (human action)   | w/ Bearer token
        +------------------+------------------+
                           |
                  +--------v--------+
                  | connectors/     |  only local_http remains
                  | local_http.py   |  (github/email pruned)
                  +-----------------+
```

### 3.1 Routine A (`routine_a.py`)
- Runs as a one-off (it is invoked directly; the schedule concept is modeled by
  the enforced iteration/time limits in the state file).
- Creates a dedicated branch (`a/draft-N`), writes `drafts/draft-N.md` and
  `drafts/review-N.json` with `review_state = "pending"`.
- Commits the draft on its branch. **It never calls Routine B and never sets
  approval.** Its only job is to produce a reviewable artifact.

### 3.2 Human approval gate (`approve.py`)
- A **separate, manual** action. It flips `review_state` from `pending` to
  `approved` and records *who* approved (`approved_by`) and *how*
  (`approved_via = "approve.py"`).
- Neither Routine A nor the API trigger ever invokes it. The API trigger
  refuses to act until this gate has been passed.

### 3.3 Routine B API trigger (`api_b.py`)
- A `ThreadingHTTPServer` listening on `127.0.0.1:8731` (configurable).
- `POST /trigger` requires `Authorization: Bearer <token>`.
- Two hard gates before any action:
  1. **401** if the token is missing/invalid.
  2. **403 refusal** if the draft `review_state != "approved"`.
- Only when both pass does it perform the follow-up: check out the draft
  branch, append `APPLIED by Routine B`, commit the draft **and** the review
  artifact together, and append a JSON evidence line to `b_transcript.log`. B
  deliberately stays on the draft branch (the reviewable unit) and never
  switches branches or pushes.

### 3.4 State file (`loop_state.json`)
- Explicitly chosen in `config.json` (`"state_file": "loop_state.json"`).
- Records `iterations`, `deadline`, and the live status of A (`a.*`) and B
  (`b.*`), plus A3 token bookkeeping. It is the single source of truth for the
  harness and is inspected by the A6 checklist.

### 3.5 Bearer-token handling (`a3_setup.py`)
- Token is generated with `secrets.token_hex(24)` **only on first run**.
- Written immediately to the **gitignored** `secrets/b_token.txt`.
- **Displayed exactly once** in the initial A3 output. Re-running A3 reads the
  stored token silently and does **not** print it again.
- The `curl` command shown by A3 is what the human uses to fire B.

### 3.6 Connector registry (`connectors/`)
- Proposed registry contained `github`, `email`, `local_http`.
- Unused connectors were **pruned**; only `local_http` (the localhost HTTP
  trigger) remains. `config.json` `enabled_connectors` matches (`["local_http"]`).
- The final state is inspectable: `connectors/` contains only `__init__.py`
  and `local_http.py`.

### 3.7 Loop limits (`loopcore.py` + `config.json`)
- Hard cap: **maximum 10 iterations OR maximum 20 minutes**, whichever comes
  first.
- Enforced by `loopcore.check_limits()`, called at the start of Routine A. When
  either limit is reached, the routine stops with a clear message. The deadline
  is recorded in `loop_state.json` at first run.

---

## 4. Repository Structure (inside `project-11/`)

| Path | Purpose |
|------|---------|
| `config.json` | Loop configuration: chosen state file, `unrestricted_push: false`, enabled connectors, B API host/port/path, iteration & time limits. |
| `loop_state.json` | The explicitly chosen state file; records iterations, deadline, A/B status, A3 token state. |
| `loopcore.py` | Shared helpers: config/state load, hard-limit enforcement, git wrapper that refuses `push` when disabled. |
| `routine_a.py` | Routine A: one-off draft producer (branch + `review_state=pending`). Never triggers B. |
| `a3_setup.py` | A3 step: generates/stores/shows bearer token once; prints the `curl` command. |
| `approve.py` | Separate human approval gate; flips `pending` → `approved` with audit metadata. |
| `api_b.py` | Routine B API trigger server; enforces token + approval gates; performs follow-up; writes transcript. |
| `checklist_a6.py` | A6 evidence-based checklist (10 items, PASS/FAIL/PENDING, no fabrication). |
| `connectors/__init__.py` | Connector registry and disk-inspection helper. |
| `connectors/local_http.py` | The single remaining connector (localhost HTTP). |
| `secrets/b_token.txt` | Generated bearer token (gitignored, untracked). |
| `drafts/draft-1.md` | Reviewable draft produced by Routine A. |
| `drafts/review-1.json` | Review artifact carrying `review_state` and approval audit. |
| `b_transcript.log` | Append-only evidence log written by Routine B on each real fire. |
| `tests/test_boundary.py` | Build-time test of the B security boundary (no real fire). |
| `.gitignore` | Ignores `secrets/`, `b_transcript.log`, `__pycache__`. |

---

## 5. Execution Flow (actual sequence)

1. **A3 setup** — `python a3_setup.py` generates the bearer token, stores it in
   `secrets/b_token.txt`, displays it **once**, and prints the `curl` command.
   The token is never printed again on later runs.
2. **Routine A draft** — `python routine_a.py` creates branch `a/draft-1`,
   writes `drafts/draft-1.md` + `drafts/review-1.json`, and commits with
   `review_state = "pending"`.
3. **`review_state = pending`** — confirmed in `loop_state.json` and
   `review-1.json`. B is armed (server can be started) but will refuse.
4. **Human approval** — `python approve.py --draft 1 --who Hafsa` flips the
   state to `approved` and records `approved_by = Hafsa`,
   `approved_via = approve.py`.
5. **API trigger fired** — the human runs the A3 `curl` against
   `http://127.0.0.1:8731/trigger` with the bearer token.
6. **Routine B follow-up** — B verifies token + approval, appends the approval
   note to the draft on `a/draft-1`, commits the draft and the review artifact
   together (staying on the draft branch), and writes a JSON evidence line to
   `b_transcript.log`.
7. **Transcript evidence** — `b_transcript.log` contains the follow-up event
   with `approval_state_at_fire = "approved"` and `approved_by = "Hafsa"`.
8. **A6 checklist** — `python checklist_a6.py` verifies all 10 items against
   real evidence; final result **PASS: 10, FAIL: 0, PENDING: 0**.

---

## 6. Security and Safety Controls

- **Token generated/stored once, not reprinted.** `a3_setup.py` prints the
  token only on first generation. A re-run reads it silently and prints
  `"A3 already configured. Token already stored; not printed again."` (verified).
- **Token gitignored / not tracked.** `secrets/` is in `.gitignore`;
  `git ls-files secrets` returns nothing. The token never enters any tracked
  file or the README.
- **B rejects missing/invalid tokens.** `POST /trigger` returns **401** for a
  missing or wrong bearer token.
- **B refuses to act before approval.** With a valid token but a draft still
  `pending`, B returns **403** with `refused: draft not in 'approved' state`.
  The API trigger alone is **not** approval.
- **Unrestricted pushes disabled.** `config.json` contains
  `unrestricted_push: false`. `loopcore.git()` raises if any `git push` is
  attempted. No push to any remote was performed.
- **No external/cloud API fabricated.** Everything is localhost-only; no
  network calls to third-party services, and no successful/“simulated” external
  API responses were invented.
- **Loop limit: 10 iterations / 20 minutes.** Enforced by
  `check_limits()`; confirmed to stop at 10 iterations and past the deadline.
- **Connector pruning.** `github` and `email` connectors were removed; only
  `local_http` remains and is the only connector referenced by config.

---

## 7. Verification / Evidence (actual)

The loop was run end-to-end and the following real evidence was observed.

**Routine B API response (`curl` fire):**
```json
{
  "ok": true,
  "evidence": {
    "event": "routine_b_followup",
    "draft_no": 1,
    "branch": "a/draft-1",
    "commit": "d70d7f0010cdcb68d57c79f228e083ac04418c79",
    "approval_state_at_fire": "approved",
    "approved_by": "Hafsa",
    "timestamp": 1787235462.8127882
  }
}
```

**`b_transcript.log` (verbatim evidence line):**
```json
{"event": "routine_b_followup", "draft_no": 1, "branch": "a/draft-1", "commit": "d70d7f0010cdcb68d57c79f228e083ac04418c79", "approval_state_at_fire": "approved", "approved_by": "Hafsa", "timestamp": 1787235462.8127882}
```

- Routine B API response showed `"ok": true` ✔
- `approval_state_at_fire` was `"approved"` ✔
- `approved_by` was `"Hafsa"` ✔
- B produced a follow-up commit (`d70d7f0 Routine B applied follow-up to draft #1`) ✔
- A6 final result: **PASS: 10, FAIL: 0, PENDING: 0** ✔

### A6 checklist output (final)
```
[PASS] A produced reviewable draft
[PASS] B exists with API trigger
[PASS] B not run prematurely
[PASS] Human changed approval state
[PASS] B transcript proves follow-up
[PASS] Bearer token not tracked
[PASS] Unrestricted pushes disabled
[PASS] Connectors pruned
[PASS] State file chosen and present
[PASS] Loop limits present and enforced
SUMMARY: {'PASS': 10, 'FAIL': 0, 'PENDING': 0}
```

---

## 8. The Human Gate — Why B Could Not Run Prematurely

Routine B has **two independent gates** that must both pass before any action:

1. A valid bearer token (proves the caller knows the secret from A3).
2. `review_state == "approved"` (proves a human explicitly approved).

The approval is set **only** by `approve.py`, a separate manual step. Routine A
never sets it; the API trigger never sets it. During testing, firing B with a
valid token while the draft was still `pending` returned **403 refusal** and
wrote **no** transcript entry — proving B cannot run merely because A ran or
because a token holder called the endpoint. B ran only on the explicit,
separate sequence: human approval → human-fired `curl`.

---

## 9. Testing Performed

1. **Token / security-boundary tests** (`tests/test_boundary.py`): started the
   B server, then asserted:
   - no token → **401**
   - wrong token → **401**
   - valid token but `pending` → **403 refusal**
   - B status remained `not_run` (no premature fire)
   Result: **ALL PASS**.
2. **Premature B execution refusal:** confirmed B writes no transcript and
   performs no git action until approval is present.
3. **Loop-limit enforcement:** `check_limits()` returned stop at 10 iterations
   and past the 20-minute deadline; passed within limits.
4. **A6 checklist:** evidence-based verification of all 10 items; final **PASS:
   10, FAIL: 0, PENDING: 0**.
5. **Final successful B execution:** after human approval, the `curl` fire
   returned `ok: true`, produced commit `d70d7f0`, and wrote the transcript
   evidence shown in section 7.

---

## 10. How To Run Locally

> Prerequisites: Python 3.10+, `git`, `curl` (use `curl.exe` in PowerShell).
> Work from inside `project-11/`.

**A3 setup — generate/store the token (shown once) and print the curl command**
```bash
python a3_setup.py
# => prints BEARER TOKEN once and the curl command to fire B later
```

**Routine A — produce a reviewable draft (pending)**
```bash
python routine_a.py
```

**Start Routine B (arms the API trigger; does NOT fire it)**
```bash
python api_b.py
# leave this running in its own terminal
```

**Approve the draft (the human gate)**
```bash
python approve.py --draft 1 --who <your-name>
```

**Fire Routine B with curl (use the token shown by A3)**
```bash
curl -sS -X POST "http://127.0.0.1:8731/trigger" \
  -H "Authorization: Bearer <BEARER_TOKEN>"
```
*(The token is read from `secrets/b_token.txt`; it is never committed or
printed after the one-time A3 display.)*

**Run the A6 evidence checklist**
```bash
python checklist_a6.py
```

> Note: no `git push` is ever performed; `unrestricted_push` is `false`.

---

## 11. Completion Criteria & Final Status

| # | Completion condition | Status |
|---|----------------------|--------|
| 1 | B ran only because its API trigger was explicitly fired | ✅ Met — fired via explicit `curl` after approval |
| 2 | B's transcript proves the follow-up action happened | ✅ Met — `b_transcript.log` + commit `d70d7f0` |
| 3 | A6 checklist run against both routines | ✅ Met — 10/10 PASS |
| 4 | Connectors pruned | ✅ Met — only `local_http` remains |
| 5 | Unrestricted pushes disabled | ✅ Met — `unrestricted_push: false`, no push executed |
| 6 | A state file explicitly chosen | ✅ Met — `loop_state.json` chosen in config |

**Final status: COMPLETE.** All six completion conditions satisfied and
confirmed by real execution and the A6 evidence checklist (PASS: 10, FAIL: 0,
PENDING: 0).

---

## 12. What This Project Demonstrates

Project 11 is a compact illustration of core **loop-engineering** principles:

- **Human gates** — automation is paused at a review boundary; a separate
  manual approval step is required before any consequential action.
- **API triggers** — Routine B is driven by an explicit, token-protected HTTP
  trigger rather than by implicit chaining from A.
- **State** — a single, explicitly chosen state file tracks iterations,
  deadlines, and per-routine status, making the loop observable and auditable.
- **Harness constraints** — hard limits (10 iterations / 20 minutes) bound
  autonomous behavior and guarantee termination.
- **Evidence** — every claim is backed by an artifact (draft, transcript,
  commit, checklist), and the A6 checklist verifies *evidence*, not mere file
  existence.
- **Controlled automation** — connectors are pruned to what is actually used,
  pushes are disabled, secrets are gitignored, and no external integration is
  assumed to exist. The result is a safe, reproducible, fully local loop that
  does exactly what it claims and nothing it does not.
