# Project-4: Maker-Checker Fix Loop (OpenCode)

## Purpose
This project demonstrates a **maker-checker (implementer → reviewer) fix loop** built on
OpenCode. The workflow:

- An **implementer** fixes a bug inside an isolated git worktree.
- A **separate reviewer agent** grades the resulting diff as **PASS** or **FAIL**.
- A pull request is opened **only if** the reviewer returns **PASS**.

The goal is to prove the reviewer is not a rubber stamp: it must accept a genuine fix
and reject a planted fake one.

## App Under Test
`src/cart.py` is a small shopping cart pricing module:

- `CartItem` — holds `name`, `unit_price`, and `quantity`, with a `line_total()` method.
- `subtotal(items)` — sums `line_total()` across all items.
- `apply_discount(subtotal_amount)` — applies a 10% discount when the subtotal qualifies.
- `total(items)` — combines subtotal + discount logic, rounded to 2 decimals.

The module docstring states the real spec: **discount applies at $100 OR MORE**.

## The Bug
`apply_discount` used a **strict `>`** comparison instead of **`>=`**:

```python
if subtotal_amount > 100:   # BUG: excludes exactly 100
```

So a subtotal of exactly **$100** wrongly missed the 10% discount (it stayed $100
instead of becoming $90), violating the documented spec of "discount applies at
$100 or more". This was an intentional boundary bug for the testing exercise.

## The Skill File
`.opencode/skills/fix-bug.md` instructs the implementer how to respond to a failing
test. It directs the agent to:

1. Run `pytest project-4/tests/ -v`.
2. Read the failing assertion.
3. Compare the source against the documented spec.
4. Find the root cause (watch boundary conditions like `>` vs `>=`).
5. Make the **minimal fix to the SOURCE** — never edit the test to make it pass.
6. Rerun pytest until all tests pass.
7. Write a one-paragraph summary of the fix.

The skill also states at the top that it must **never touch project-1/, project-2/,
or project-3/**.

## Loop Steps
1. **Isolate** — make the change in a dedicated git worktree so the main branch is
   untouched until review passes.
2. **Implement** — fix the bug in `src/cart.py` (the source), following the skill.
3. **Review** — hand the diff to a separate reviewer agent that grades strictly on:
   root cause fixed in source (not test), matches documented spec, no unrelated files
   changed, and confidence all tests pass for the right reason.
4. **Gate** — open a PR only when the reviewer returns **PASS**. A **FAIL** means the
   change is rejected and reworked.

## Verification

### Real fix → PASS
The implementer changed `>` to `>=` in `apply_discount`. Reviewer graded **PASS** with
reasons:
- Root cause fixed in source, not the test.
- Change matches the docstring spec ("$100 or more").
- No files outside `project-4/` touched; minimal, confident all tests pass.

### Planted bad fix → FAIL
To prove the reviewer isn't a pushover, a bad fix was planted by **editing the test's
expected value** (`90.00` → `100.00`) to match the still-buggy output, instead of fixing
the source. Reviewer graded **FAIL** with reasons:
- The test was weakened instead of the source being fixed.
- It's a hack that hides the bug; the boundary behavior is still wrong vs the spec.
- Tests pass only for the wrong reason — not the spec-correct behavior.

This proves the reviewer distinguishes a real fix from a fake one.

## File Tree
```
project-4/
├── .opencode/
│   └── skills/
│       └── fix-bug.md
├── src/
│   └── cart.py
├── tests/
│   └── test_cart.py
├── VERIFICATION.md
└── README.md
```

## Closing Note
Every agent run in this project was scoped to **only touch `project-4/`**, in accordance
with this repository's `AGENTS.md` — `project-1/`, `project-2/`, and `project-3/` were
never read, referenced, or modified.
