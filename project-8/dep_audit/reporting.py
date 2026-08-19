"""OBSERVABILITY: structured run records and human-readable reports.

Every run writes two artefacts into ``log_dir``:
  * ``run-<timestamp>-<iter>.json`` -- machine readable, for diagnostics.
  * ``run-<timestamp>-<iter>.md``   -- human readable report.

Each stage (heartbeat tick, audit, worktree, maker, checker, connector) is
logged with a status and message so failures are diagnosable.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StageLog:
    stage: str
    status: str  # ok | fail | skip | info
    message: str
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class RunResult:
    run_id: str
    iteration: int
    start_time: str
    end_time: str
    status: str            # success | noop | failed
    findings_count: int
    changes_count: int
    checker_passed: Optional[bool]
    errors: List[str] = field(default_factory=list)
    stages: List[StageLog] = field(default_factory=list)
    report_path: Optional[str] = None
    log_path: Optional[str] = None
    human_report: str = ""

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["stages"] = [s.to_dict() for s in self.stages]
        return d

    @property
    def stop(self) -> bool:
        """Tell the heartbeat whether to stop after this run.

        Only terminal states stop the loop: a failure (fail closed) or having
        nothing left to do (noop). A ``success`` keeps looping so that any
        remaining actionable findings (beyond the per-run cap) get handled in a
        later iteration, until eventually a ``noop`` is reached.
        """
        return self.status in ("failed", "noop")


class Reporter:
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def new_run(self, iteration: int) -> "RunContext":
        return RunContext(self, iteration)


class RunContext:
    def __init__(self, reporter: Reporter, iteration: int):
        self.reporter = reporter
        self.iteration = iteration
        self.run_id = uuid.uuid4().hex[:12]
        self.start_time = _now()
        self.stages: List[StageLog] = []
        self.errors: List[str] = []

    def log_stage(self, stage: str, status: str, message: str = "") -> None:
        self.stages.append(StageLog(stage=stage, status=status, message=message))

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def finalize(
        self,
        status: str,
        findings_count: int = 0,
        changes_count: int = 0,
        checker_passed: Optional[bool] = None,
        human_report: str = "",
    ) -> RunResult:
        end_time = _now()
        result = RunResult(
            run_id=self.run_id,
            iteration=self.iteration,
            start_time=self.start_time,
            end_time=end_time,
            status=status,
            findings_count=findings_count,
            changes_count=changes_count,
            checker_passed=checker_passed,
            errors=self.errors,
            stages=self.stages,
            human_report=human_report,
        )
        ts = self.start_time.replace(":", "").replace("-", "").replace(".", "")[:14]
        stem = f"run-{ts}-{self.iteration:04d}-{self.run_id}"
        json_path = self.reporter.log_dir / f"{stem}.json"
        md_path = self.reporter.log_dir / f"{stem}.md"
        json_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        md_path.write_text(human_report or _default_md(result), encoding="utf-8")
        result.log_path = str(json_path)
        result.report_path = str(md_path)

        # Also append a single-line index entry for quick scanning.
        idx = self.reporter.log_dir / "index.log"
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(
                f"{self.start_time} iter={self.iteration} status={status} "
                f"findings={findings_count} changes={changes_count} "
                f"checker={checker_passed} run_id={self.run_id}\n"
            )
        return result


def _default_md(result: RunResult) -> str:
    lines = [
        f"# Dependency Audit Run {result.run_id}",
        "",
        f"- **Iteration:** {result.iteration}",
        f"- **Status:** {result.status}",
        f"- **Started:** {result.start_time}",
        f"- **Ended:** {result.end_time}",
        f"- **Findings:** {result.findings_count}",
        f"- **Changes:** {result.changes_count}",
        f"- **Checker passed:** {result.checker_passed}",
        "",
        "## Stage log",
        "",
        "| Stage | Status | Message |",
        "|-------|--------|---------|",
    ]
    for s in result.stages:
        lines.append(f"| {s.stage} | {s.status} | {s.message} |")
    if result.errors:
        lines += ["", "## Errors", ""]
        lines += [f"- {e}" for e in result.errors]
    return "\n".join(lines) + "\n"
