#!/usr/bin/env bash
#
# candidate-2.sh  -- a COMPLETE fix attempt.
# Fixes all three bugs (subtract, multiply, divide). The reviewer should PASS.
#
set -uo pipefail
WT="${1:?usage: candidate-2.sh <worktree-dir>}"
PYTHON="$(command -v python || command -v python3)"

"$PYTHON" - "$WT" <<'PY'
import sys
wt = sys.argv[1]
path = wt + "/calc.py"
src = open(path).read()
src = src.replace("return a - b + 1", "return a - b")
src = src.replace("return a + b  # BUG: should multiply", "return a * b")
src = src.replace("return a // b  # BUG: integer division, should be true division", "return a / b")
open(path, "w").write(src)
print("candidate-2: fixed subtract, multiply, divide")
PY
