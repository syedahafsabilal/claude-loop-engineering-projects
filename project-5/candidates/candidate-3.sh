#!/usr/bin/env bash
#
# candidate-3.sh  -- another PARTIAL fix attempt.
# Fixes only the `multiply` bug. `subtract` and `divide` stay broken, so the
# reviewer will FAIL this candidate (for different reasons than candidate-1).
#
set -uo pipefail
WT="${1:?usage: candidate-3.sh <worktree-dir>}"
PYTHON="$(command -v python || command -v python3)"

"$PYTHON" - "$WT" <<'PY'
import sys
wt = sys.argv[1]
path = wt + "/calc.py"
src = open(path).read()
src = src.replace("return a + b  # BUG: should multiply", "return a * b")
open(path, "w").write(src)
print("candidate-3: fixed multiply only")
PY
