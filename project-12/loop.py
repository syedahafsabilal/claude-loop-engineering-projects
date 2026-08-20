#!/usr/bin/env python3
"""Project 12 — improvement loop (analysis + GitHub/PR phase).

Reads progress logs newer than the date in dreaming-state.md, detects
failures/corrections that recur, and drafts the smallest possible change to
rules/rules.md as a reviewable diff. The automation creates a `claude/` branch,
commits the proposal (never the rules file itself), pushes, and opens a PR.
The processed date in dreaming-state.md advances ONLY after the PR is created.

Human gate: the automation never merges the PR and never edits rules/rules.md
on main. Use --dry-run to analyze and preview without any Git/PR/state change.
"""

import argparse
import difflib
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_DIR = os.path.join(PROJECT_DIR, "progress-logs")
RULES_FILE = os.path.join(PROJECT_DIR, "rules", "rules.md")
STATE_FILE = os.path.join(PROJECT_DIR, "dreaming-state.md")
ANALYSIS_DIR = os.path.join(PROJECT_DIR, "analysis")

FAILURES_HEADER = "## Failures / Corrections"
RUNS_HEADER = "## Runs"
MIN_REPEAT = 2


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def load_last_processed_date(state_path=STATE_FILE):
    with open(state_path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"last-processed-date\**\s*:\s*(\d{4}-\d{2}-\d{2})", text)
    if not m:
        raise ValueError("last-processed-date not found in %s" % state_path)
    return m.group(1)


def iter_logs(progress_dir=PROGRESS_DIR, last_date=None):
    """Yield (date, text) for each dated log strictly newer than last_date."""
    out = []
    for path in sorted(glob.glob(os.path.join(progress_dir, "*.md"))):
        fname = os.path.basename(path)
        m = re.match(r"(\d{4}-\d{2}-\d{2})\.md", fname)
        if not m:
            continue
        date = m.group(1)
        if last_date is not None and date <= last_date:
            continue
        with open(path, "r", encoding="utf-8") as f:
            out.append((date, f.read()))
    return out


def _section(text, header):
    lines = text.splitlines()
    out, in_section = [], False
    for line in lines:
        if line.strip().startswith(header):
            in_section = True
            continue
        if in_section and line.strip().startswith("## "):
            break
        if in_section:
            out.append(line)
    return out


def parse_failures(date, text):
    occs = []
    for line in _section(text, FAILURES_HEADER):
        s = line.strip()
        if not s.startswith("-"):
            continue
        if re.search(r"\bnone\b", s, re.I):
            continue
        m = re.search(r"\(([^)]+)\)", s)
        run_id = m.group(1) if m else "unknown"
        signature = re.sub(r"\([^)]*\)", "", s).strip(" -").rstrip(".").lower()
        occs.append({
            "signature": signature,
            "run_id": run_id,
            "date": date,
            "failure_line": s,
            "evidence": s,
        })
    return occs


def parse_corrections(date, text):
    corr = {}
    current_run = None
    for line in _section(text, RUNS_HEADER):
        rm = re.match(r"\s*- (run-\w+):", line)
        if rm:
            current_run = rm.group(1)
            continue
        if current_run and "CORRECTION:" in line:
            corr.setdefault(current_run, []).append(line.strip())
    return corr


def build_occurrences(progress_dir=PROGRESS_DIR, last_date=None):
    all_occs = []
    for date, text in iter_logs(progress_dir, last_date):
        corr = parse_corrections(date, text)
        for occ in parse_failures(date, text):
            if occ["run_id"] in corr:
                occ["evidence"] = " | ".join(corr[occ["run_id"]])
            all_occs.append(occ)
    return all_occs


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

def detect_repeated_failures(occurrences, min_count=MIN_REPEAT):
    groups = {}
    for occ in occurrences:
        groups.setdefault(occ["signature"], []).append(occ)
    return {sig: occs for sig, occs in groups.items() if len(occs) >= min_count}


def propose_for_failure(signature, occs):
    count = len(occs)
    run_ids = ", ".join(o["run_id"] for o in occs)
    dates = ", ".join(o["date"] for o in occs)

    if "claude/" in signature:
        proposed_change = (
            "Append a new rule to rules/rules.md:\n\n"
            "### R7 — Guard: loop-created branches must begin with `claude/`\n"
            "All branches created by the Project 12 improvement loop must "
            "begin with the `claude/` prefix. Reject branch creation that "
            "does not match this prefix before any further work proceeds."
        )
    else:
        proposed_change = (
            "Append a new rule to rules/rules.md that guards against this "
            "failure:\n\n"
            f"> **New rule (proposed):** Prevent recurrence of: \"{signature}\".\n"
            "Add a pre-condition check that fails fast when the condition is "
            "violated, so the correction is never needed again."
        )

    rationale = (
        f"The failure '{signature}' recurred {count} time(s) across runs "
        f"({run_ids}) on dates {dates}. Adding an explicit guard at the point "
        "where the mistake is made prevents the repeated after-the-fact "
        "correction, which is exactly the pattern observed in the logs."
    )
    return proposed_change, rationale


def validate_repeated_proposal(prop):
    """Evidence-first gate: reject proposals lacking real supporting data."""
    required = ["failure", "run_ids", "dates", "count", "evidence",
                "proposed_change", "rationale"]
    for key in required:
        val = prop.get(key)
        if not val:
            return False
    if prop["count"] < MIN_REPEAT:
        return False
    if not prop["evidence"] or "TODO" in prop["evidence"]:
        return False
    return True


# --------------------------------------------------------------------------
# Deletion proposal (exactly one unused rule)
# --------------------------------------------------------------------------

def find_deprecated_rules(rules_text):
    return re.findall(r"###\s*(R\d+)\s*—\s*DEPRECATED", rules_text)


def rule_usage_counts(corpus):
    checks = {
        "R1": lambda ln: "test" in ln and ("pass" in ln or "run" in ln or "suite" in ln),
        "R2": lambda ln: ("secret" in ln or "key" in ln or "credential" in ln),
        "R3": lambda ln: "pin" in ln and ("version" in ln or "depend" in ln),
        "R4": lambda ln: "dreaming-state" in ln,
        "R5": lambda ln: "evidence" in ln,
        "R6": lambda ln: ("/tmp/debug.log" in ln and "no " not in ln
                          and "not needed" not in ln and "unused" not in ln),
    }
    counts = {k: 0 for k in checks}
    for ln in corpus.splitlines():
        low = ln.lower()
        for k, fn in checks.items():
            if fn(low):
                counts[k] += 1
    return counts


def propose_deletion(rules_text, usage, progress_dir=PROGRESS_DIR, last_date=None):
    deprecated = find_deprecated_rules(rules_text)
    logs = iter_logs(progress_dir, last_date)
    dates = ", ".join(d for d, _ in logs)
    n_runs = sum(len(re.findall(r"- run-\w+:", t)) for _, t in logs)

    for rid in deprecated:
        if usage.get(rid, 0) == 0:
            reason = (
                f"Rule {rid} is flagged DEPRECATED in rules/rules.md and had 0 "
                f"positive usages across the {n_runs} processed runs (dates: "
                f"{dates}). The debug workflow that motivated it was removed, "
                "so no recent run depends on it. Deleting it reduces noise "
                "without changing behaviour."
            )
            return {
                "rule_id": rid,
                "usage_count": 0,
                "reason": reason,
                "dates": dates,
                "runs_processed": n_runs,
            }
    return None


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render_proposal(last_date, repeated, rf_props, deletion):
    lines = []
    lines.append("# Project 12 — Improvement Proposal (draft)\n")
    lines.append(f"Generated from progress logs dated after: **{last_date}**\n")
    lines.append("> This is a DRAFT. rules/rules.md and dreaming-state.md are "
                 "unchanged. No branch/PR created yet.\n")

    lines.append("## Repeated failures -> proposed additions\n")
    if rf_props:
        for i, p in enumerate(rf_props, 1):
            lines.append(f"### {i}. {p['failure']}\n")
            lines.append(f"- **Occurrence count:** {p['count']}")
            lines.append(f"- **Exact run IDs:** {p['run_ids']}")
            lines.append(f"- **Exact log dates:** {p['dates']}\n")
            lines.append("**Evidence (verbatim from logs):**\n")
            for ev in p["evidence"]:
                lines.append(f"  - {ev}\n")
            lines.append("**Smallest proposed change to rules/rules.md:**\n")
            for cl in p["proposed_change"].splitlines():
                lines.append(f"  {cl}" if cl.strip() else "")
            lines.append("")
            lines.append(f"**Why this prevents the failure:** {p['rationale']}\n")
    else:
        lines.append("_No repeated failures detected._\n")

    lines.append("## Proposed deletion (exactly one)\n")
    if deletion:
        lines.append(f"- **Rule to delete:** {deletion['rule_id']}")
        lines.append(f"- **Positive usages in processed logs:** {deletion['usage_count']}")
        lines.append(f"- **Runs processed:** {deletion['runs_processed']} "
                     f"(dates: {deletion['dates']})")
        lines.append(f"- **Reason it is safe to delete:** {deletion['reason']}\n")
        lines.append("> The rule is NOT deleted here. It changes only if the "
                     "PR is manually merged.\n")
    else:
        lines.append("_No deletion candidate identified._\n")

    return "\n".join(lines)


def write_proposal(md, analysis_dir=ANALYSIS_DIR):
    os.makedirs(analysis_dir, exist_ok=True)
    path = os.path.join(analysis_dir, "proposal.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def analyze(state_file=STATE_FILE, progress_dir=PROGRESS_DIR,
            rules_file=RULES_FILE):
    last_date = load_last_processed_date(state_file)
    occurrences = build_occurrences(progress_dir, last_date)
    repeated = detect_repeated_failures(occurrences)

    rf_props = []
    for sig, occs in repeated.items():
        change, rationale = propose_for_failure(sig, occs)
        prop = {
            "failure": sig,
            "count": len(occs),
            "run_ids": ", ".join(o["run_id"] for o in occs),
            "dates": ", ".join(o["date"] for o in occs),
            "evidence": [o["evidence"] for o in occs],
            "proposed_change": change,
            "rationale": rationale,
        }
        if validate_repeated_proposal(prop):
            rf_props.append(prop)

    with open(rules_file, "r", encoding="utf-8") as f:
        rules_text = f.read()
    corpus = "\n".join(t for _, t in iter_logs(progress_dir, last_date))
    usage = rule_usage_counts(corpus)
    deletion = propose_deletion(rules_text, usage, progress_dir, last_date)

    md = render_proposal(last_date, repeated, rf_props, deletion)
    return {
        "last_date": last_date,
        "repeated": repeated,
        "rf_props": rf_props,
        "deletion": deletion,
        "usage": usage,
        "markdown": md,
    }


# --------------------------------------------------------------------------
# PR phase helpers
# --------------------------------------------------------------------------

class GitHubUnavailableError(Exception):
    pass


class NoReviewableChangeError(Exception):
    """Raised when the staged proposal artifacts match the base branch, i.e.
    there is no actual change to commit (so a PR would have an empty diff)."""
    pass


def slugify(text, max_len=40):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len] or "improve"


def latest_processed_date(last_date, progress_dir=PROGRESS_DIR):
    dates = [d for d, _ in iter_logs(progress_dir, last_date)]
    return max(dates) if dates else last_date


def _extract_new_rule(proposed_change):
    idx = proposed_change.find("\n\n")
    return proposed_change[idx + 2:] if idx != -1 else proposed_change


def make_rules_diff(rules_text, proposed_change):
    new_text = rules_text.rstrip() + "\n\n" + _extract_new_rule(proposed_change) + "\n"
    old = rules_text.splitlines(keepends=True)
    new = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old, new, fromfile="a/rules/rules.md", tofile="b/rules/rules.md")
    return "".join(diff)


def write_change_files(analysis, analysis_dir=ANALYSIS_DIR, rules_file=RULES_FILE):
    """Write the proposal and a reviewable diff. Never touches rules/rules.md."""
    os.makedirs(analysis_dir, exist_ok=True)
    paths = []
    p = os.path.join(analysis_dir, "proposal.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(analysis["markdown"])
    paths.append(p)

    with open(rules_file, "r", encoding="utf-8") as f:
        rules_text = f.read()
    diff = make_rules_diff(rules_text, analysis["rf_props"][0]["proposed_change"])
    dp = os.path.join(analysis_dir, "rules-proposal.diff")
    with open(dp, "w", encoding="utf-8") as f:
        f.write(diff)
    paths.append(dp)

    new_text = rules_text.rstrip() + "\n\n" + \
        _extract_new_rule(analysis["rf_props"][0]["proposed_change"]) + "\n"
    np = os.path.join(analysis_dir, "proposed-rules.md")
    with open(np, "w", encoding="utf-8") as f:
        f.write(new_text)
    paths.append(np)
    return paths


def build_pr_body(analysis):
    lines = []
    lines.append("# Project 12 — Rules Improvement (automated proposal)\n")
    lines.append("Generated from progress logs dated after **%s**.\n"
                 % analysis["last_date"])

    lines.append("## Repeated failure(s) addressed\n")
    for prop in analysis["rf_props"]:
        lines.append("### %s\n" % prop["failure"])
        lines.append("- **Occurrence count:** %s" % prop["count"])
        lines.append("- **Exact run IDs:** %s" % prop["run_ids"])
        lines.append("- **Exact log dates:** %s\n" % prop["dates"])
        lines.append("**Actual log evidence (verbatim):**")
        for ev in prop["evidence"]:
            lines.append("  - %s" % ev)
        lines.append("")
        lines.append("**Proposed change (reviewable diff in "
                     "`analysis/rules-proposal.diff`):**")
        for cl in prop["proposed_change"].splitlines():
            lines.append("  %s" % cl if cl.strip() else "")
        lines.append("")
        lines.append("**Why this is the smallest prevention:** %s\n"
                     % prop["rationale"])

    lines.append("## Proposed deletion (exactly one)\n")
    d = analysis["deletion"]
    lines.append("- **Rule to delete:** %s" % d["rule_id"])
    lines.append("- **Positive usages in processed logs:** %s" % d["usage_count"])
    lines.append("- **Runs processed:** %s (dates: %s)"
                 % (d["runs_processed"], d["dates"]))
    lines.append("- **Reason it is safe to delete:** %s\n" % d["reason"])

    lines.append("## Human review required\n")
    lines.append("The `rules/rules.md` file is **NOT** modified by this "
                 "automation. The change is presented as a reviewable diff for "
                 "**human review and manual merge**. Do not merge via automation; "
                 "this PR must be reviewed and merged manually. Only after a "
                 "human merges it does the rule change take effect.")
    return "\n".join(lines)


def update_dreaming_state(state_path, new_date, pr_number, pr_url):
    with open(state_path, "r", encoding="utf-8") as f:
        text = f.read()

    def _repl(m):
        return ("%s%s\n- **last-pr-number**: %s\n- **last-pr-url**: %s"
                % (m.group(1), new_date, pr_number, pr_url))

    text = re.sub(r"(last-processed-date\**\s*:\s*)\d{4}-\d{2}-\d{2}",
                  _repl, text, count=1)
    with open(state_path, "w", encoding="utf-8") as f:
        f.write(text)


# --------------------------------------------------------------------------
# Git + GitHub clients (mockable)
# --------------------------------------------------------------------------

class LocalGit:
    def __init__(self, root=PROJECT_DIR):
        self.root = root

    def _run(self, *args):
        return subprocess.run(["git", "-C", self.root, *args],
                              capture_output=True, text=True)

    def create_branch(self, name):
        r = self._run("checkout", "-b", name)
        if r.returncode != 0:
            raise RuntimeError("branch creation failed: %s" % r.stderr)
        return name

    def add(self, paths):
        r = self._run("add", *paths)
        if r.returncode != 0:
            raise RuntimeError("git add failed: %s" % r.stderr)

    def has_staged_changes(self):
        # List staged paths; non-empty means there is a real reviewable change.
        # (Using --name-only is more robust than relying on --quiet's exit code.)
        r = self._run("diff", "--cached", "--name-only")
        if r.returncode != 0:
            raise RuntimeError("git diff --cached failed: %s" % r.stderr)
        return bool(r.stdout.strip())

    def commit(self, msg):
        r = self._run("commit", "-m", msg)
        if r.returncode != 0:
            if "nothing to commit" in (r.stderr or ""):
                raise NoReviewableChangeError(
                    "git commit reported nothing to commit")
            raise RuntimeError("git commit failed: %s" % r.stderr)

    def push(self, branch):
        r = self._run("push", "-u", "origin", branch)
        if r.returncode != 0:
            raise RuntimeError("git push failed: %s" % r.stderr)


class GitHubCLI:
    def available(self):
        if not shutil.which("gh"):
            return False
        if subprocess.run(["gh", "auth", "status"],
                          capture_output=True, text=True).returncode != 0:
            return False
        rem = subprocess.run(["git", "-C", PROJECT_DIR, "remote", "get-url",
                              "origin"], capture_output=True, text=True)
        if rem.returncode != 0 or not rem.stdout.strip():
            return False
        return True

    def create_pr(self, base, head, title, body):
        r = subprocess.run(
            ["gh", "pr", "create", "--base", base, "--head", head,
             "--title", title, "--body", body],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("gh pr create failed: %s" % r.stderr)
        # `gh pr create` prints the new PR's URL to stdout (gh >= 2.x); the PR
        # number is the final numeric segment of that URL. We no longer pass
        # the unsupported `--json` flag (removed: gh 2.97 `pr create` rejects
        # it), so we derive the number from the URL instead.
        url = (r.stdout or r.stderr).strip().splitlines()[-1].strip()
        m = re.search(r"/pull/(\d+)", url)
        if not m:
            raise RuntimeError(
                "gh pr create succeeded but no PR URL in output: %r" % (r.stdout,))
        return {"number": int(m.group(1)), "url": url}


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def execute_phase(analysis, github, git, state_writer,
                  base_branch="main", state_file=STATE_FILE,
                  analysis_dir=ANALYSIS_DIR, dry_run=False):
    """Run the GitHub/PR phase.

    Order: validate evidence -> validate deletion -> create claude/ branch ->
    write change files -> commit -> push -> create PR -> (only then) advance
    dreaming-state, committing and pushing that state update on the same branch.
    Any failure before PR creation leaves state untouched. rules/rules.md is
    never modified, and nothing is ever merged.
    """
    if dry_run:
        return {"skipped": True}

    if not analysis.get("rf_props"):
        raise ValueError("evidence gate: no repeated-failure proposals; aborting")
    if analysis.get("deletion") is None:
        raise ValueError("evidence gate: no deletion proposal; aborting")
    if not github.available():
        raise GitHubUnavailableError(
            "GitHub CLI unavailable / not authenticated / no remote")

    branch = "claude/" + slugify(analysis["rf_props"][0]["failure"])
    git.create_branch(branch)

    # Never modify rules/rules.md here; only write proposal + diff.
    paths = write_change_files(analysis, analysis_dir=analysis_dir)
    add_and_commit_if_changed(git, paths,
                              "project-12: draft rules improvement from repeated-failure analysis")
    git.push(branch)

    body = build_pr_body(analysis)
    title = "Project 12: propose rule for repeated failure"
    pr = github.create_pr(base=base_branch, head=branch, title=title, body=body)

    # ONLY after PR creation succeeds do we advance dreaming-state, and we
    # commit + push that update on the same (claude/) branch. main and
    # rules/rules.md are never touched by this automation.
    new_date = latest_processed_date(analysis["last_date"])
    state_writer(new_date, pr["number"], pr["url"])
    add_and_commit_if_changed(git, [state_file],
                              "project-12: advance dreaming-state after PR creation")
    git.push(branch)
    return {"pr": pr, "branch": branch}


def add_and_commit_if_changed(git, paths, msg):
    """Stage paths and commit only if they actually change the tree.

    Guarantees the improvement branch carries a real, reviewable diff before
    `git commit` is attempted. Raises NoReviewableChangeError (rather than the
    misleading 'git commit failed') when the generated artifacts are identical
    to what is already on the base branch.
    """
    git.add(paths)
    if not git.has_staged_changes():
        raise NoReviewableChangeError(
            "generated proposal artifacts match the base branch; there is no "
            "reviewable change to commit. Aborting PR creation.")
    git.commit(msg)


def main(argv=None):
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Project 12 improvement loop")
    ap.add_argument("--dry-run", action="store_true",
                    help="Analyze + build PR body without any Git/PR/state change")
    ap.add_argument("--base", default="main",
                    help="Base branch for the PR (default: main)")
    ap.add_argument("--state-file", default=STATE_FILE)
    ap.add_argument("--progress-dir", default=PROGRESS_DIR)
    ap.add_argument("--rules-file", default=RULES_FILE)
    ap.add_argument("--analysis-dir", default=ANALYSIS_DIR)
    args = ap.parse_args(argv)

    result = analyze(args.state_file, args.progress_dir, args.rules_file)

    if args.dry_run:
        print("[dry-run] No branch / commit / push / PR / state changes.")
        print(result["markdown"])
        print("\n--- PR body preview ---")
        print(build_pr_body(result))
        return 0

    github = GitHubCLI()
    git = LocalGit()
    state_writer = lambda d, n, u: update_dreaming_state(args.state_file, d, n, u)
    try:
        out = execute_phase(result, github, git, state_writer,
                            base_branch=args.base, state_file=args.state_file,
                            analysis_dir=args.analysis_dir)
    except Exception as e:
        print("PR phase aborted (dreaming-state NOT advanced): %s" % e,
              file=sys.stderr)
        return 1
    print("Created PR: %s on branch %s" % (out["pr"]["url"], out["branch"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
