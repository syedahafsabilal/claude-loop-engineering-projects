"""Build-time test of Routine B's security boundary.

Verifies, WITHOUT firing B for real:
  - POST with no/invalid bearer -> 401
  - POST with valid bearer but draft NOT approved -> 403 refusal
The approved-path (which actually performs the follow-up) is intentionally
NOT exercised here; it requires the human gate and is done later.
"""

import json
import os
import sys
import threading
import time
import http.client

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api_b
from loopcore import load_config, load_state, BASE_DIR, secrets_dir


def _post(token):
    cfg = load_config()
    conn = http.client.HTTPConnection(cfg["b_api"]["host"], cfg["b_api"]["port"], timeout=5)
    headers = {}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    conn.request("POST", cfg["b_api"]["path"], headers=headers)
    r = conn.getresponse()
    body = r.read().decode()
    conn.close()
    return r.status, body


def main():
    cfg = load_config()
    token = open(os.path.join(secrets_dir(), "b_token.txt")).read().strip()

    srv = threading.Thread(target=api_b.run_server, daemon=True)
    srv.start()
    time.sleep(1.0)

    out = []

    # 1. No token -> 401
    s, b = _post(None)
    out.append(("no token -> 401", s == 401, s))

    # 2. Wrong token -> 401
    s, b = _post("wrong-token")
    out.append(("wrong token -> 401", s == 401, s))

    # 3. Valid token but not approved -> 403 refusal (boundary holds)
    s, b = _post(token)
    refused = (s == 403) and ("refused" in b.lower())
    out.append(("valid token, not approved -> 403 refusal", refused, s))

    # Confirm B did NOT actually run (no fire recorded).
    state = load_state()
    no_fire = state.get("b", {}).get("status") == "not_run"
    out.append(("B not fired by boundary test", no_fire, state["b"]["status"]))

    print("BOUNDARY TEST RESULTS:")
    for name, ok, got in out:
        print("  [%s] %s (got=%s)" % ("PASS" if ok else "FAIL", name, got))

    failed = [n for n, ok, _ in out if not ok]
    print("RESULT:", "ALL PASS" if not failed else ("FAIL: " + ", ".join(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
