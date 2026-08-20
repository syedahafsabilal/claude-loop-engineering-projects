"""Routine B: API-triggered follow-up.

Security boundary enforced in POST /trigger:
  1. Must carry a valid bearer token (else 401).
  2. The draft review_state MUST be 'approved' (else 403 refusal). The API
     trigger alone does NOT equal approval.

Only when both pass does B perform its small follow-up action and write a
transcript that proves the action happened.

Run the server (the trigger endpoint) with:
    python api_b.py
B's action only occurs when a human fires the A3 curl after approval.
"""

import json
import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from loopcore import load_config, load_state, save_state, git, BASE_DIR
from connectors.local_http import load_token


def latest_review():
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


def perform_followup():
    """The actual follow-up action. Returns an evidence dict."""
    state = load_state()
    draft_no, review = latest_review()

    # Hard refusal if not approved. The API trigger alone is not approval.
    if review is None or review.get("review_state") != "approved":
        raise PermissionError("refused: draft not in 'approved' state")

    branch = state["a"]["branch"]
    draft_rel = state["a"]["draft"]
    review_rel = "drafts/review-%d.json" % draft_no
    draft_abs = os.path.join(BASE_DIR, draft_rel)

    # Follow-up: apply an approval note to the draft on its own branch.
    git(["checkout", branch])
    with open(draft_abs, "a") as f:
        f.write("\n---\nAPPLIED by Routine B at %s (human-approved follow-up).\n"
                % time.strftime("%Y-%m-%dT%H:%M:%S"))
    git(["add", draft_rel, review_rel])
    res = git(["commit", "-m", "Routine B applied follow-up to draft #%d" % draft_no])
    commit_hash = ""
    if res.returncode == 0:
        out = git(["rev-parse", "HEAD"])
        commit_hash = out.stdout.strip()
    # B performs its follow-up on the draft branch (the reviewable unit) and
    # intentionally does NOT switch branches or push. The human reviews/merges
    # the branch separately. This avoids any implicit branch manipulation.

    evidence = {
        "event": "routine_b_followup",
        "draft_no": draft_no,
        "branch": branch,
        "commit": commit_hash,
        "approval_state_at_fire": review.get("review_state"),
        "approved_by": review.get("approved_by"),
        "timestamp": time.time(),
    }

    transcript_path = os.path.join(BASE_DIR, "b_transcript.log")
    with open(transcript_path, "a") as f:
        f.write(json.dumps(evidence) + "\n")

    state["b"] = {
        "status": "ran",
        "fired": True,
        "approved_before_fire": True,
        "transcript": os.path.relpath(transcript_path, BASE_DIR),
    }
    save_state(state)
    return evidence


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # keep token out of server logs

    def do_POST(self):
        cfg = load_config()
        path = cfg["b_api"]["path"]
        if self.path != path:
            self.send_response(404)
            self.end_headers()
            return

        auth = self.headers.get("Authorization", "")
        token_path = os.path.join(BASE_DIR, "secrets", "b_token.txt")
        expected = load_token(os.path.join(BASE_DIR, "secrets")) if os.path.exists(token_path) else ""

        if not auth.startswith("Bearer ") or auth[len("Bearer "):].strip() != expected:
            body = b'{"error":"invalid or missing bearer token"}'
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return

        try:
            evidence = perform_followup()
            body = json.dumps({"ok": True, "evidence": evidence}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        except PermissionError as e:
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)


def run_server():
    cfg = load_config()
    srv = ThreadingHTTPServer((cfg["b_api"]["host"], cfg["b_api"]["port"]), Handler)
    print("Routine B API trigger listening on http://%s:%d%s (armed, not fired)" %
          (cfg["b_api"]["host"], cfg["b_api"]["port"], cfg["b_api"]["path"]))
    srv.serve_forever()


if __name__ == "__main__":
    run_server()
