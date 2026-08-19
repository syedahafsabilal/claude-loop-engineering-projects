# Project 6 — Event-driven GitHub PR review loop with OpenCode

> "Make your throwaway repo review its own pull requests."

This project demonstrates an **event-driven code-review loop**: opening or
updating a pull request automatically triggers [OpenCode](https://opencode.ai)
to review the changes and post its findings as a comment on the PR.

> **Test note:** This README is being used to test the automated PR-review
> workflow — a small, harmless edit to `project-6/README.md` triggers the
> `opencode-pr-review` workflow on a PR (and again on each `synchronize` push).

## What was created inside `project-6/`

| File | Purpose |
| --- | --- |
| `calculator.py` | Small module with a deliberately planted bug (`max_value` returns the minimum instead of the maximum). |
| `test_calculator.py` | Unit tests that **pass** — they do not cover `max_value`, so the bug is invisible to CI and must be caught by review. |
| `.github/workflows/opencode-review.yml` | The OpenCode PR-review workflow (canonical copy). |
| `opencode.json` | OpenCode permission config used when running locally. |
| `scripts/install-workflow.ps1` | Promotes the workflow to the repo-root `.github/workflows/` so GitHub runs it. |
| `README.md` | This file. |

## The planted bug

`calculator.py` defines `max_value(values)`, which is supposed to return the
largest element of a list. Its loop updates the running result with the
**smallest** value seen because the comparison is inverted:

```python
result = values[0]
for v in values[1:]:
    if v < result:   # BUG: should be `v > result`
        result = v
return result
```

The local test suite only exercises `mean` and `divide`, so it stays green and
the bug slips past CI. A code review (human or OpenCode) reading the function
immediately sees that `<` should be `>`.

## GitHub / OpenCode workflow configured

The workflow uses the official action **`anomalyco/opencode/github@latest`**
and triggers on the `pull_request` event with these activity types:

- `opened` — first review when the PR is created.
- `synchronize` — **the heartbeat**: every new commit pushed to the PR branch
  re-runs the review.
- `reopened`, `ready_for_review` — additional entry points.

It runs on `ubuntu-latest`, is path-scoped to `project-6/**` (so it only fires
for this project), and authenticates with `GITHUB_TOKEN` plus an
`ANTHROPIC_API_KEY` secret. OpenCode posts its review as a PR comment, so it is
visible on GitHub. A custom `prompt` tells OpenCode to read the full file,
hunt for the planted logic bug, and report file/line/suggested-fix.

For `pull_request` events the action defaults to reviewing the PR, and
`use_github_token: true` makes the review comment appear under the PR.

## How to test the event-driven PR review

1. **Activate the workflow** (GitHub only runs workflows from the repo root):
   ```powershell
   pwsh project-6/scripts/install-workflow.ps1
   git add .github/workflows/opencode-review.yml
   ```
2. **Add the `ANTHROPIC_API_KEY` secret** in the repo:
   *Settings → Secrets and variables → Actions → New repository secret*.
3. **Open a PR that introduces `project-6/`** (e.g. the initial commit adding
   this folder), or simply push the project-6 files on a branch and open a PR.
4. **Watch the review appear**: the `opencode-pr-review` workflow runs and
   OpenCode posts a comment on the PR identifying the `max_value` bug
   (`v < result` → `v > result`).
5. **Test the synchronize heartbeat**: push another commit to the PR branch.
   The `synchronize` event fires and OpenCode reviews again, posting a fresh
   comment — confirming the loop re-triggers on each update.

## Scope

No files outside `project-6/` were created or modified by this work. The only
step that touches the repository root (`.github/workflows/opencode-review.yml`)
is performed by the user via `scripts/install-workflow.ps1`, because GitHub
requires workflows at the repo root to execute; it does not touch any other
project folder.
