"""A3 setup step: create the Routine B API trigger and emit the bearer token ONCE.

Rules enforced here:
- Token is generated fresh only if it does not already exist.
- It is written immediately to the gitignored secrets location.
- It is displayed exactly once (on first generation). On later runs the token
  is read silently and is NOT printed again, so it never leaks into normal
  output or transcripts.
- The exact curl command the human will use to fire B is printed.
- This step does NOT start the server and does NOT fire B.
"""

import os
import secrets
import time

from loopcore import load_config, load_state, save_state, secrets_dir, BASE_DIR


def main():
    cfg = load_config()
    state = load_state()
    token_path = os.path.join(secrets_dir(), "b_token.txt")

    generated_now = False
    if not os.path.exists(token_path):
        token = secrets.token_hex(24)
        os.makedirs(secrets_dir(), exist_ok=True)
        with open(token_path, "w") as f:
            f.write(token)
        generated_now = True
        state["a3"]["token_generated"] = True
    else:
        # Token already exists: read silently. Do NOT print it again.
        with open(token_path) as f:
            token = f.read().strip()

    if generated_now:
        state["a3"]["token_shown_once"] = True
        state["chosen_at"] = state.get("chosen_at") or time.strftime("%Y-%m-%dT%H:%M:%S")
    # The token (whether generated just now or already present) is available.
    state["a3"]["token_generated"] = True

    b = cfg["b_api"]
    url = "http://{host}:{port}{path}".format(**b)
    curl_cmd = (
        'curl -sS -X POST "%s" -H "Authorization: Bearer %s"'
    ) % (url, token)

    save_state(state)

    if generated_now:
        print("=== A3: Routine B API trigger configured ===")
        print("BEARER TOKEN (shown ONCE, store it now): %s" % token)
        print("Secret also written to: %s (gitignored)" % token_path)
        print("")
        print("Human fires Routine B later with:")
        print(curl_cmd)
        print("")
        print("IMPORTANT: B will REFUSE unless the draft review_state is 'approved'.")
    else:
        print("A3 already configured. Token already stored; not printed again.")
        print("Human fires Routine B with the curl command from the first A3 run.")


if __name__ == "__main__":
    main()
