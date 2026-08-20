"""Explicit human approval gate.

This is a SEPARATE human action. Routine A never calls it, and the API
trigger never calls it. It flips the review_state from 'pending' to
'approved' and records that a human did it (approved_by / approved_via).

Usage:
    python approve.py --draft <n> --who <human-id>
"""

import argparse
import json
import os
import time

from loopcore import load_config, save_state, BASE_DIR


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draft", type=int, required=True)
    p.add_argument("--who", default="human", help="human identifier performing approval")
    args = p.parse_args()

    review_path = os.path.join(BASE_DIR, "drafts", "review-%d.json" % args.draft)
    if not os.path.exists(review_path):
        raise SystemExit("review artifact not found: %s" % review_path)

    with open(review_path) as f:
        review = json.load(f)

    if review["review_state"] != "pending":
        raise SystemExit("draft #%d is not in 'pending' state (current=%s)"
                         % (args.draft, review["review_state"]))

    review["review_state"] = "approved"
    review["approved_by"] = args.who
    review["approved_via"] = "approve.py"
    review["approved_at"] = time.time()
    with open(review_path, "w") as f:
        json.dump(review, f, indent=2)

    # Reflect approval in the loop state too.
    from loopcore import load_state
    state = load_state()
    state["a"]["review_state"] = "approved"
    save_state(state)

    print("HUMAN APPROVAL recorded for draft #%d by '%s'." % (args.draft, args.who))
    print("Review state is now 'approved'. Routine B may now be fired.")


if __name__ == "__main__":
    main()
