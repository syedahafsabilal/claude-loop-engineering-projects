#!/usr/bin/env bash
#
# fix-and-review.sh
#
# Codifies a "draft candidate fixes in parallel, then review" workflow.
#
# For every candidate listed in the config file (candidates.list by default):
#   1. create an isolated git worktree (separate directory) so candidates
#      cannot collide with each other,
#   2. launch that candidate's fix attempt in the BACKGROUND (parallel),
#   3. `wait` until every fix attempt has finished,
#   4. run a per-candidate "reviewer" (reviewer.sh) whose exit code is the
#      verdict (0 = pass, nonzero = fail),
#   5. print a clear PASS/FAIL summary.
#
# This script intentionally keeps NO state between runs: no state file, no
# history, no memory. Each run tears down and rebuilds everything from the
# committed source in sample-project/. See README.md.
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAMPLE="$ROOT/sample-project"
CONFIG="${1:-$ROOT/candidates.list}"
WORKDIR="$ROOT/worktrees"
LOGDIR="$ROOT/logs"

# --- locate a python interpreter -------------------------------------------
PYTHON="$(command -v python || command -v python3)"
if [ -z "$PYTHON" ]; then
  echo "ERROR: python3/python not found on PATH" >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found on PATH" >&2
  exit 1
fi

mkdir -p "$LOGDIR"

# --- fresh start: tear down any worktrees/branches from a previous run ------
# (This is cleanup of output artifacts, NOT reading any persisted state.)
# We ONLY ever remove the isolated $WORKDIR we created; the source repo in
# $SAMPLE is never touched, so a previous run can never delete our source.
cd "$SAMPLE" || exit 1
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"
git worktree prune
while read -r name _; do
  [ -z "$name" ] && continue
  case "$name" in \#*) continue ;; esac
  git branch -D "$name" >/dev/null 2>&1 || true
done < "$CONFIG"

echo "=================================================================="
echo " fix-and-review : drafting candidate fixes in parallel, then review"
echo " config : $CONFIG"
echo " sample : $SAMPLE"
echo " python : $PYTHON"
echo "=================================================================="

# --- phase 1: create worktrees + launch fix attempts in the background ------
declare -a PIDS=()
declare -a NAMES=()
i=0
while read -r name script; do
  [ -z "$name" ] && continue
  case "$name" in \#*) continue ;; esac

  echo "[setup] $name -> worktree $WORKDIR/$name"
  if ! git worktree add -b "$name" "$WORKDIR/$name" HEAD >/dev/null 2>&1; then
    echo "  ERROR: could not create worktree for $name" >&2
    continue
  fi

  (
    echo "[fix] $name: starting"
    bash "$ROOT/$script" "$WORKDIR/$name" > "$LOGDIR/$name.fix.log" 2>&1
    echo "[fix] $name: finished (exit $?)"
  ) &

  PIDS[$i]=$!
  NAMES[$i]=$name
  i=$((i + 1))
done < "$CONFIG"

echo "[wait] blocking until all $i fix attempts finish..."
for pid in "${PIDS[@]}"; do
  wait "$pid"
done
echo "[wait] all fix attempts finished."

# --- phase 2: review each finished candidate -------------------------------
declare -A VERDICT=()
declare -A NOTE=()
for name in "${NAMES[@]}"; do
  echo "[review] $name ..."
  bash "$ROOT/reviewer.sh" "$WORKDIR/$name" > "$LOGDIR/$name.review.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    VERDICT[$name]="PASS"
    NOTE[$name]="all checks passed"
  else
    VERDICT[$name]="FAIL"
    NOTE[$name]="reviewer exited $rc (see $LOGDIR/$name.review.log)"
  fi
done

# --- summary ----------------------------------------------------------------
echo ""
echo "=================================================================="
echo " SUMMARY"
echo "=================================================================="
printf "%-14s %-6s %s\n" "CANDIDATE" "RESULT" "NOTES"
for name in "${NAMES[@]}"; do
  printf "%-14s %-6s %s\n" "$name" "${VERDICT[$name]}" "${NOTE[$name]}"
done
echo "=================================================================="

# exit nonzero if any candidate failed, so the script is CI-friendly
for name in "${NAMES[@]}"; do
  [ "${VERDICT[$name]}" = "PASS" ] || exit 2
done
exit 0
