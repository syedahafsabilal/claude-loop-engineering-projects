#!/usr/bin/env bash
#
# candidate-1.sh  -- a PARTIAL fix attempt.
# Fixes only the off-by-one bug in `subtract`. `multiply` and `divide`
# remain broken, so the reviewer (test suite) will still FAIL this candidate.
#
set -uo pipefail
WT="${1:?usage: candidate-1.sh <worktree-dir>}"
PYTHON="$(command -v python || command -v python3)"

"$PYTHON" - "$WT" <<'PY'
import sys
wt = sys.argv[1]
path = wt + "/calc.py"
src = open(path).read()
src = src.replace("return a - b + 1", "return a - b")
open(path, "w").write(src)
print("candidate-1: fixed subtract (off-by-one) only")
PY
