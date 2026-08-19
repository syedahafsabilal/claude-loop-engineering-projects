"""Command line entry point for the dependency-audit loop.

Usage
-----
Single run (one audit + maker + checker + connector):
    python -m dep_audit.cli run --dry-run

Unattended loop (heartbeat drives the spine until caught up / budget hit):
    python -m dep_audit.cli loop --dry-run

Real GitHub PRs (credentials from env, repo configured):
    python -m dep_audit.cli loop --no-dry-run --repo owner/name
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import LoopConfig
from .heartbeat import Heartbeat
from .reporting import Reporter
from .spine import Spine

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _build_config(args) -> LoopConfig:
    cfg = LoopConfig.defaults(PROJECT_ROOT)
    if args.config:
        cfg = cfg.load_from_file(Path(args.config))
    # CLI overrides (only when explicitly provided).
    if args.target:
        cfg.target_dir = Path(args.target)
    if args.registry:
        cfg.registry_path = Path(args.registry)
    if args.log_dir:
        cfg.log_dir = Path(args.log_dir)
    if args.backend:
        cfg.worktree_backend = args.backend
    if args.max_iterations is not None:
        cfg.max_iterations = args.max_iterations
    if args.max_runtime is not None:
        cfg.max_runtime_seconds = args.max_runtime
    if args.max_changes is not None:
        cfg.max_changes_per_run = args.max_changes
    if args.interval is not None:
        cfg.interval_seconds = args.interval
    if args.allow_major:
        cfg.allow_major = True
    if args.dry_run is not None:
        cfg.dry_run = args.dry_run
    if args.repo:
        cfg.github_repo = args.repo
    return cfg


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="path to a JSON config file")
    parser.add_argument("--target", help="directory containing manifest.json")
    parser.add_argument("--registry", help="path to registry.json")
    parser.add_argument("--log-dir", help="directory for run logs/reports")
    parser.add_argument("--backend", choices=["copy", "git"], help="worktree backend")
    parser.add_argument("--max-iterations", type=int, help="heartbeat iteration cap")
    parser.add_argument("--max-runtime", type=float, help="loop wall-clock cap (s)")
    parser.add_argument("--max-changes", type=int, help="max dependency changes per run")
    parser.add_argument("--interval", type=float, help="seconds between heartbeats")
    parser.add_argument("--allow-major", action="store_true",
                        help="permit major-version upgrades (forbidden by default)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        default=None, help="do NOT push / open PRs (safe; default)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                        help="actually push / open PRs (credentials required)")
    parser.add_argument("--repo", help="owner/name for real GitHub PRs")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="dep_audit")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run the loop once")
    _add_common(p_run)

    p_loop = sub.add_parser("loop", help="run the loop on a heartbeat schedule")
    _add_common(p_loop)

    args = parser.parse_args(argv)
    cfg = _build_config(args)
    reporter = Reporter(cfg.log_dir)

    spine = Spine(cfg, reporter=reporter)

    if args.command == "run":
        result = spine.run_once(0)
        print(result.human_report)
        print(f"\n[run] status={result.status} findings={result.findings_count} "
              f"changes={result.changes_count} checker={result.checker_passed}")
        print(f"[run] report: {result.report_path}")
        print(f"[run] log:    {result.log_path}")
        return 0 if result.status != "failed" else 1

    # loop mode
    hb = Heartbeat(cfg, spine.run_once)
    summary = hb.run()
    print(f"[loop] stopped: {summary.stop_reason}")
    print(f"[loop] runs={summary.total_runs} last_status={summary.last_status}")
    print(f"[loop] run_ids={[r.run_id for r in summary.results]}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
