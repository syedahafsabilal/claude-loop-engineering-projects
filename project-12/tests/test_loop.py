#!/usr/bin/env python3
"""Tests for the Project 12 local analysis loop.

Run from anywhere:  python -m tests.test_loop   (or)  pytest tests/
All tests read only from project-12/ and assert that protected files
(rules/rules.md, dreaming-state.md) are NOT modified.
"""

import os
import re
import sys
import unittest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import loop  # noqa: E402

RULES_FILE = os.path.join(PROJECT_DIR, "rules", "rules.md")
STATE_FILE = os.path.join(PROJECT_DIR, "dreaming-state.md")


class TestAnalysis(unittest.TestCase):

    def setUp(self):
        self.last = loop.load_last_processed_date(STATE_FILE)
        self.occs = loop.build_occurrences(loop.PROGRESS_DIR, self.last)
        self.repeated = loop.detect_repeated_failures(self.occs)
        with open(RULES_FILE, encoding="utf-8") as f:
            rules_text = f.read()
        corpus = "\n".join(t for _, t in loop.iter_logs(loop.PROGRESS_DIR, self.last))
        self.usage = loop.rule_usage_counts(corpus)
        self.deletion = loop.propose_deletion(rules_text, self.usage,
                                              loop.PROGRESS_DIR, self.last)

    def test_repeated_failure_detection(self):
        self.assertIn("forgot to prefix branch with `claude/`", self.repeated)

    def test_occurrence_count(self):
        occs = self.repeated["forgot to prefix branch with `claude/`"]
        self.assertEqual(len(occs), 4)

    def test_exact_run_and_date_evidence(self):
        occs = self.repeated["forgot to prefix branch with `claude/`"]
        run_ids = {o["run_id"] for o in occs}
        dates = {o["date"] for o in occs}
        self.assertEqual(run_ids, {"run-001", "run-003", "run-007", "run-010"})
        self.assertEqual(dates, {"2026-08-13", "2026-08-14",
                                 "2026-08-16", "2026-08-18"})
        for o in occs:
            self.assertIn("CORRECTION:", o["evidence"])
            self.assertTrue(o["evidence"].strip())

    def test_reject_unsupported_proposal(self):
        bad = {
            "failure": "x", "count": 1, "run_ids": "",
            "dates": "", "evidence": "", "proposed_change": "", "rationale": "",
        }
        self.assertFalse(loop.validate_repeated_proposal(bad))
        good = {
            "failure": "forgot to prefix branch with `claude/`",
            "count": 4, "run_ids": "run-001",
            "dates": "2026-08-13",
            "evidence": ["CORRECTION: opened branch `fix/x`"],
            "proposed_change": "add rule", "rationale": "prevents recurrence",
        }
        self.assertTrue(loop.validate_repeated_proposal(good))

    def test_exactly_one_deletion(self):
        self.assertIsNotNone(self.deletion)
        self.assertEqual(self.deletion["rule_id"], "R6")
        self.assertEqual(self.deletion["usage_count"], 0)

    def test_rules_unchanged(self):
        before = loop.sha256(RULES_FILE)
        loop.analyze()  # full run must not touch rules
        after = loop.sha256(RULES_FILE)
        self.assertEqual(before, after)

    def test_last_processed_date_unchanged(self):
        before = loop.load_last_processed_date(STATE_FILE)
        loop.analyze()
        after = loop.load_last_processed_date(STATE_FILE)
        self.assertEqual(before, after)

    def test_dry_run_writes_nothing(self):
        proposal_path = os.path.join(loop.ANALYSIS_DIR, "proposal.md")
        existed_before = os.path.exists(proposal_path)
        loop.main(argv=["--dry-run"])
        exists_after = os.path.exists(proposal_path)
        self.assertEqual(existed_before, exists_after)


# --------------------------------------------------------------------------
# Mock layer for the GitHub/PR phase (no real branch/commit/push/PR)
# --------------------------------------------------------------------------

class FakeGitHub:
    def __init__(self, avail=True, fail=False):
        self._avail = avail
        self.fail = fail
        self.calls = []

    def available(self):
        return self._avail

    def create_pr(self, base, head, title, body):
        if self.fail:
            raise RuntimeError("PR creation failed")
        self.calls.append({"base": base, "head": head,
                           "title": title, "body": body})
        return {"number": 42, "url": "https://example.com/PR/42"}


class FakeGit:
    def __init__(self, current="main"):
        self.current = current
        self.branch_created = None
        self.added = []
        self.committed = False
        self.pushed = []

    def create_branch(self, name):
        self.branch_created = name
        self.current = name

    def add(self, paths):
        self.added.extend(paths)

    def commit(self, msg):
        self.committed = True

    def push(self, branch):
        self.pushed.append(branch)


class FakeState:
    def __init__(self):
        self.calls = []

    def __call__(self, new_date, pr_number, pr_url):
        self.calls.append((new_date, pr_number, pr_url))


class TestPrPhase(unittest.TestCase):

    def setUp(self):
        self.result = loop.analyze()

    def test_branch_starts_with_claude(self):
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        out = loop.execute_phase(self.result, gh, git, st)
        self.assertTrue(git.branch_created.startswith("claude/"))
        self.assertIn("claude/", out["branch"])

    def test_pr_body_contains_required_evidence(self):
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        loop.execute_phase(self.result, gh, git, st)
        body = gh.calls[0]["body"]
        needles = [
            "forgot to prefix branch with `claude/`", "4",
            "run-001", "run-003", "run-007", "run-010",
            "2026-08-13", "2026-08-14", "2026-08-16", "2026-08-18",
            "CORRECTION:", "smallest prevention",
            "R6", "safe to delete", "human review", "merge",
        ]
        for n in needles:
            self.assertIn(n, body)

    def test_pr_body_exactly_one_deletion(self):
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        loop.execute_phase(self.result, gh, git, st)
        body = gh.calls[0]["body"]
        self.assertEqual(body.count("## Proposed deletion"), 1)
        self.assertEqual(body.count("**Rule to delete:**"), 1)

    def test_rules_not_modified_by_automation(self):
        before = loop.sha256(loop.RULES_FILE)
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        loop.execute_phase(self.result, gh, git, st)
        self.assertEqual(loop.sha256(loop.RULES_FILE), before)

    def test_merge_blocked(self):
        self.assertFalse(hasattr(loop.GitHubCLI, "merge"))
        self.assertFalse(hasattr(loop.GitHubCLI, "merge_pr"))
        with open(loop.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("pr merge", src)
        self.assertNotIn("merge_pr", src)

    def test_state_does_not_advance_when_pr_fails(self):
        before = loop.sha256(loop.STATE_FILE)
        gh, git, st = FakeGitHub(fail=True), FakeGit(), FakeState()
        with self.assertRaises(RuntimeError):
            loop.execute_phase(self.result, gh, git, st)
        self.assertEqual(st.calls, [])
        self.assertEqual(loop.sha256(loop.STATE_FILE), before)

    def test_state_advances_after_success(self):
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        loop.execute_phase(self.result, gh, git, st)
        self.assertEqual(len(st.calls), 1)
        new_date, num, url = st.calls[0]
        self.assertEqual(new_date, "2026-08-19")  # latest processed log date
        self.assertEqual(num, 42)
        self.assertEqual(url, "https://example.com/PR/42")
        self.assertTrue(git.branch_created.startswith("claude/"))

    def test_no_direct_main_rules_commit(self):
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        loop.execute_phase(self.result, gh, git, st)
        self.assertTrue(git.branch_created.startswith("claude/"))
        norm = [p.replace("\\", "/") for p in git.added]
        self.assertNotIn(loop.RULES_FILE.replace("\\", "/"), norm)
        for p in norm:
            self.assertNotIn("rules/rules.md", p)

    def test_validation_failure_blocks_everything(self):
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        bad = dict(self.result)
        bad["rf_props"] = []
        with self.assertRaises(ValueError):
            loop.execute_phase(bad, gh, git, st)
        self.assertIsNone(git.branch_created)
        self.assertEqual(st.calls, [])

    def test_dry_run_no_side_effects(self):
        gh, git, st = FakeGitHub(), FakeGit(), FakeState()
        out = loop.execute_phase(self.result, gh, git, st, dry_run=True)
        self.assertIn("skipped", out)
        self.assertIsNone(git.branch_created)
        self.assertEqual(st.calls, [])
        self.assertEqual(gh.calls, [])


if __name__ == "__main__":
    unittest.main()
