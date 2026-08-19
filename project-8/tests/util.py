"""Shared helpers for the test suite (no real network / credentials needed)."""

from pathlib import Path

from dep_audit.config import LoopConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def base_config(**overrides) -> LoopConfig:
    cfg = LoopConfig.defaults(PROJECT_ROOT)
    cfg.worktree_backend = "copy"
    cfg.dry_run = True
    cfg.allow_major = False
    cfg.max_changes_per_run = 5
    cfg.max_iterations = 10
    cfg.max_runtime_seconds = 3600.0
    cfg.interval_seconds = 0.0
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg
