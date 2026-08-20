"""Shared helpers for the project-11 human-gated loop.

Handles config + state loading, the enforced hard limits (max 10 iterations
OR 20 minutes), and a guarded git wrapper that refuses unrestricted pushes.
"""

import json
import os
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(BASE_DIR, "config.json")) as f:
        return json.load(f)


def load_state():
    with open(os.path.join(BASE_DIR, "loop_state.json")) as f:
        return json.load(f)


def save_state(state):
    with open(os.path.join(BASE_DIR, "loop_state.json"), "w") as f:
        json.dump(state, f, indent=2)


def secrets_dir():
    return os.path.join(BASE_DIR, "secrets")


def check_limits(state):
    """Enforce the hard cap: max 10 iterations OR 20 minutes.

    Returns (ok, reason). If not ok, the caller must stop.
    """
    cfg_limits = load_config()["limits"]
    max_iter = cfg_limits["max_iterations"]
    max_min = cfg_limits["max_minutes"]

    if state.get("iterations", 0) >= max_iter:
        return False, "iteration limit reached (%d)" % max_iter

    deadline = state.get("deadline")
    if deadline is not None and time.time() > deadline:
        return False, "time limit reached (%d min)" % max_min

    return True, ""


def git(args, cwd=BASE_DIR):
    """Run a git command. Push is blocked unless explicitly enabled in config."""
    import subprocess
    if args and args[0] == "push":
        cfg = load_config()
        if not cfg.get("unrestricted_push", False):
            raise RuntimeError("unrestricted push is disabled; refusing 'git push'")
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
