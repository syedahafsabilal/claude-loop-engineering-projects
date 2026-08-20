# project-9 routine: daily commit summary (DELIBERATELY BROKEN — v2)

BEFORE doing anything else, you MUST read the file:

project-9/nonexistent-input.txt

This file is required input for the task. Base all subsequent work on its
contents. If you cannot read this file (for example, because it does not exist),
the task MUST fail and you MUST explicitly report failure — do not proceed with
summarizing commits or creating any branch/commit as a workaround.

Only if the file is successfully read, then:
1. Determine yesterday's date range using local time.
2. Run the appropriate git log command to inspect yesterday's commits.
3. If there are no commits, write "No commits found for yesterday." to SUMMARY.md.
4. Create or checkout a branch named `claude/summary`.
5. Create or update `SUMMARY.md` with the summary of yesterday's commits.
6. Commit `SUMMARY.md` to the `claude/summary` branch.
7. Report the number of commits summarized and the resulting commit hash.
