#!/usr/bin/env bash
#
# reviewer.sh  -- the per-candidate "checker"
#
# Runs the sample project's test suite inside a candidate's worktree.
# Exit code 0 = PASS, any nonzero = FAIL. That exit code IS the grade.
#
set -uo pipefail

TARGET="${1:?usage: reviewer.sh <candidate-worktree-dir>}"
[ -d "$TARGET" ] || { echo "reviewer: no such directory: $TARGET" >&2; exit 2; }

PYTHON="$(command -v python || command -v python3)"
[ -n "$PYTHON" ] || { echo "reviewer: python not found" >&2; exit 2; }

cd "$TARGET" || exit 2
exec "$PYTHON" test_calc.py
