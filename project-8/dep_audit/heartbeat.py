"""HEARTBEAT: scheduled, repeatable trigger for the loop.

The heartbeat drives the spine repeatedly. It enforces two budget guards that
nothing else does:
  * ``max_iterations`` -- hard cap on how many times the loop runs.
  * ``max_runtime_seconds`` -- wall-clock cap for a single `loop` invocation.

Between iterations it sleeps ``interval_seconds`` (or can be driven externally,
e.g. by cron / systemd timers -- see README). It always stops safely on
failure or when the spine reports there is nothing left to do.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .config import LoopConfig
from .reporting import RunResult


@dataclass
class HeartbeatSummary:
    total_runs: int = 0
    stop_reason: str = ""
    last_status: str = ""
    results: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "stop_reason": self.stop_reason,
            "last_status": self.last_status,
            "run_ids": [r.run_id for r in self.results],
        }


class Heartbeat:
    def __init__(self, config: LoopConfig, on_tick: Callable[[int], RunResult]):
        self.config = config
        self.on_tick = on_tick

    def run(self) -> HeartbeatSummary:
        summary = HeartbeatSummary()
        start = time.monotonic()
        iteration = 0
        while iteration < self.config.max_iterations:
            if time.monotonic() - start > self.config.max_runtime_seconds:
                summary.stop_reason = "max_runtime_seconds reached"
                break
            try:
                result = self.on_tick(iteration)
            except Exception as exc:  # fail closed: a stage blew up -> stop
                summary.stop_reason = f"exception in tick: {exc}"
                summary.last_status = "failed"
                break
            summary.total_runs += 1
            summary.results.append(result)
            summary.last_status = result.status
            if result.stop:
                summary.stop_reason = f"spine requested stop (status={result.status})"
                break
            iteration += 1
            if iteration < self.config.max_iterations:
                time.sleep(self.config.interval_seconds)
        if not summary.stop_reason:
            summary.stop_reason = "max_iterations reached"
        return summary
