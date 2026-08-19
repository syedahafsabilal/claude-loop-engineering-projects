# project-3

A scheduled loop that maintains a progress log. It reads `progress.md`, scans the repo (excluding all other project-N folders) for TODO comments, compares findings against every previously logged entry, and appends a new dated section containing only what is new.

## Files
- `task.md` — the instructions the loop follows each run.
- `progress.md` — the memory log; one dated entry per run summarizing new TODOs.
- `notes.md` — a test TODO used to verify the loop works (it was correctly detected and logged on the run after it was added).

## Status
Tested by running it multiple times; runs after the first correctly omit TODOs already recorded, confirming prior findings are not repeated.
