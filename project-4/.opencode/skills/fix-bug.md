---
name: fix-bug-project-4
description: Diagnose and fix a failing test in project-4's cart pricing module.
---

IMPORTANT: This skill must NEVER read, open, edit, or touch project-1/, project-2/,
or project-3/ for any reason. Only operate inside project-4/.

Steps for diagnosing and fixing a failing test in project-4:

1. Run pytest for the project:
   `pytest project-4/tests/ -v`
2. Read the failing assertion message to understand which test failed and what
   value was produced versus expected.
3. Compare the implementation in project-4/src/cart.py against the spec stated
   in its module docstring (discount applies at $100 OR MORE).
4. Find the root cause — pay attention to boundary conditions (e.g. a strict `>`
   that should be `>=`).
5. Make the MINIMAL fix to the SOURCE code (project-4/src/cart.py). Never edit
   the test to make it pass; the test describes correct behavior.
6. Rerun `pytest project-4/tests/ -v` until all tests pass.
7. Write a one-paragraph summary of the fix: what the bug was, why it failed at
   the boundary, and what change resolved it.
