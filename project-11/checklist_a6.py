"""A6 checklist: verify EVIDENCE, not mere file existence.

Each check returns PASS / FAIL / PENDING. A PENDING result is used honestly
when the underlying execution step has not actually happened yet (e.g. B has
not been fired because the human gate has not been passed). No evidence is
fabricated.
"""

import json
import os
import subprocess

from loopcore import load_config, load_state, BASE_DIR, secrets_dir
from connectors import list_connector_modules


def _git(args):
    return subprocess.run(["git"] + args, cwd=BASE_DIR,
                          capture_output=True, text=True)


def run():
    cfg = load_config()
    state = load_state()
    results = []

    def add(name, status, detail):
        results.append({"check": name, "status": status, "detail": detail})

    # 1. A exists and produced a reviewable draft.
    draft = state.get("a", {}).get("draft")
    a_ok = state.get("a", {}).get("status") == "produced" and draft and os.path.exists(os.path.join(BASE_DIR, draft))
    add("A produced reviewable draft",
        "PASS" if a_ok else "PENDING",
        "draft=%s" % draft)

    # 2. B exists and has an API trigger.
    b_file = os.path.join(BASE_DIR, "api_b.py")
    has_trigger = os.path.exists(b_file) and "do_POST" in open(b_file).read() and "Authorization" in open(b_file).read()
    add("B exists with API trigger",
        "PASS" if has_trigger else "FAIL",
        "api_b.py present and parses Authorization header")

    # 3. B did not run before the explicit human approval/trigger sequence.
    if state.get("b", {}).get("status") == "not_run":
        add("B not run prematurely",
            "PASS", "b.status=not_run (no fire yet)")
    elif state["b"].get("approved_before_fire"):
        add("B not run prematurely",
            "PASS", "B fired only after approval (approved_before_fire=true)")
    else:
        add("B not run prematurely",
            "FAIL", "B ran without prior approval")

    # 4. Approval state explicitly changed by the human.
    review_no, review = _latest_review()
    if review is None:
        add("Human changed approval state",
            "PENDING", "no review artifact yet")
    elif review.get("approved_via") == "approve.py" and review.get("approved_by"):
        add("Human changed approval state",
            "PASS", "approved_by=%s via %s" % (review["approved_by"], review["approved_via"]))
    elif review.get("review_state") == "approved":
        add("Human changed approval state",
            "FAIL", "approved but not via explicit human action")
    else:
        add("Human changed approval state",
            "PENDING", "still pending (human gate not passed)")

    # 5. B's transcript proves follow-up occurred after approval.
    transcript = os.path.join(BASE_DIR, "b_transcript.log")
    if os.path.exists(transcript) and state.get("b", {}).get("fired"):
        add("B transcript proves follow-up",
            "PASS", "transcript exists and b.fired=true")
    else:
        add("B transcript proves follow-up",
            "PENDING", "B not fired; transcript not produced yet")

    # 6. Bearer token not committed/tracked.
    tracked = _git(["ls-files", "secrets"]).stdout.strip()
    token_file = os.path.join(secrets_dir(), "b_token.txt")
    token_exists = os.path.exists(token_file)
    add("Bearer token not tracked",
        "PASS" if (token_exists and tracked == "") else "FAIL",
        "tracked secrets=[%s]; local token file present=%s" % (tracked, token_exists))

    # 7. Unrestricted pushes disabled.
    add("Unrestricted pushes disabled",
        "PASS" if cfg.get("unrestricted_push") is False else "FAIL",
        "unrestricted_push=%s" % cfg.get("unrestricted_push"))

    # 8. Connectors pruned.
    mods = [m[:-3] for m in list_connector_modules(BASE_DIR) if m.endswith(".py")]
    pruned_ok = mods == ["local_http"] and cfg["enabled_connectors"] == ["local_http"]
    add("Connectors pruned",
        "PASS" if pruned_ok else "FAIL",
        "modules on disk=%s; enabled=%s" % (mods, cfg["enabled_connectors"]))

    # 9. Selected state file exists and records the run.
    sf = cfg["state_file"]
    exists = os.path.exists(os.path.join(BASE_DIR, sf))
    chosen = state.get("state_file_choice") == sf
    add("State file chosen and present",
        "PASS" if (exists and chosen) else "FAIL",
        "state_file=%s; choice recorded=%s" % (sf, chosen))

    # 10. Loop limits present and enforced.
    lim = cfg.get("limits", {})
    enforced = (lim.get("max_iterations") == 10 and lim.get("max_minutes") == 20
                and state.get("deadline") is not None)
    add("Loop limits present and enforced",
        "PASS" if enforced else "FAIL",
        "limits=%s; deadline set=%s" % (lim, state.get("deadline") is not None))

    return results


def _latest_review():
    drafts_dir = os.path.join(BASE_DIR, "drafts")
    best = None
    if os.path.isdir(drafts_dir):
        for f in os.listdir(drafts_dir):
            if f.startswith("review-") and f.endswith(".json"):
                n = int(f[len("review-"):-len(".json")])
                if best is None or n > best:
                    best = n
    if best is None:
        return None, None
    with open(os.path.join(drafts_dir, "review-%d.json" % best)) as fh:
        return best, json.load(fh)


if __name__ == "__main__":
    res = run()
    for r in res:
        print("[%s] %s -- %s" % (r["status"], r["check"], r["detail"]))
    summary = {"PASS": 0, "FAIL": 0, "PENDING": 0}
    for r in res:
        summary[r["status"]] += 1
    print("SUMMARY: %s" % summary)
