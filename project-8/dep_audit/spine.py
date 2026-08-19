"""SPINE: central orchestrator.

Wires:  heartbeat -> audit -> worktree -> maker -> checker -> connector

The spine is the only place that decides whether the loop continues. It fails
closed:
  * any stage error stops the run,
  * a failed checker discards the worktree and never calls the connector,
  * a connector failure discards the worktree too.

It returns a :class:`RunResult` whose ``stop`` flag tells the heartbeat whether
to keep going.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .audit import audit, read_manifest, read_registry
from .checker import CheckResult, check
from .config import LoopConfig
from .connector import Connector, FakeConnector, GitHubConnector
from .maker import MakerResult, make
from .reporting import Reporter, RunResult
from .worktree import create_worktree


def build_connector(config: LoopConfig) -> Connector:
    # Tests inject a FakeConnector; real runs use GitHub unless explicitly
    # overridden. Defaulting to Fake when no repo is configured keeps the
    # project safe out-of-the-box.
    if config.github_repo and not config.dry_run:
        return GitHubConnector(config)
    return FakeConnector(config)


def _human_report(iteration, findings, maker_result, checker, connector_result, status) -> str:
    lines = [
        f"# Dependency Audit -- iteration {iteration}",
        "",
        f"**Result:** {status}",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for f in findings:
            mark = "ACTIONABLE" if f.actionable else "blocked"
            lines.append(f"- [{mark}] {f.dependency} {f.current} -> {f.latest} ({f.bump}): {f.reason}")
    else:
        lines.append("- none")
    lines += ["", "## Proposed changes", ""]
    if maker_result and maker_result.changes:
        for c in maker_result.changes:
            lines.append(f"- {c.dependency}: {c.old_version} -> {c.new_version} ({c.bump})"
                         + (f" [advisory {c.advisory}]" if c.advisory else ""))
    else:
        lines.append("- none")
    lines += [
        "",
        f"## Checker: {'PASSED' if (checker and checker.passed) else 'FAILED'}",
        "",
    ]
    if checker and checker.errors:
        for e in checker.errors:
            lines.append(f"- error: {e}")
    if connector_result:
        lines.append("")
        lines.append(f"## Connector (dry_run={connector_result.dry_run})")
        lines.append(f"- pushed: {connector_result.pushed}, created_pr: {connector_result.created_pr}")
        for n in connector_result.notes:
            lines.append(f"- {n}")
    return "\n".join(lines) + "\n"


class Spine:
    def __init__(self, config: LoopConfig, reporter: Optional[Reporter] = None,
                 connector: Optional[Connector] = None):
        self.config = config
        self.reporter = reporter or Reporter(config.log_dir)
        self._connector = connector

    def _connector_instance(self) -> Connector:
        return self._connector or build_connector(self.config)

    def run_once(self, iteration: int) -> RunResult:
        ctx = self.reporter.new_run(iteration)
        ctx.log_stage("heartbeat", "info", f"tick {iteration}")
        worktree = None
        maker_result: Optional[MakerResult] = None
        checker: Optional[CheckResult] = None
        connector_result = None

        try:
            # --- AUDIT (on the real target, read-only) ----------------------
            manifest = read_manifest(self.config.target_dir / "manifest.json")
            registry = read_registry(self.config.registry_path)
            findings = audit(manifest, registry, allow_major=self.config.allow_major)
            actionable = [f for f in findings if f.actionable]
            ctx.log_stage("audit", "ok",
                          f"{len(findings)} findings, {len(actionable)} actionable")

            if not actionable:
                blocked = [f for f in findings if not f.actionable]
                if blocked:
                    ctx.log_stage("audit", "info",
                                  f"{len(blocked)} finding(s) need human review "
                                  f"(e.g. major upgrades)")
                ctx.log_stage("audit", "info", "nothing actionable; done")
                return ctx.finalize("noop", findings_count=len(findings),
                                    human_report=_human_report(iteration, findings, None, None, None, "noop"))

            # --- WORKTREE (isolated) ---------------------------------------
            worktree = create_worktree(self.config.worktree_backend,
                                       self.config.target_dir, branch=f"dep-audit-{ctx.run_id}")
            ctx.log_stage("worktree", "ok", f"isolated at {worktree.path}")

            # --- MAKER -----------------------------------------------------
            maker_result = make(worktree, findings, self.config)
            ctx.log_stage("maker", "ok",
                          f"proposed {len(maker_result.changes)} change(s)")

            # --- CHECKER (independent) -------------------------------------
            checker = check(worktree, maker_result, self.config)
            ctx.log_stage("checker", "ok" if checker.passed else "fail",
                          "passed" if checker.passed else "; ".join(checker.errors))

            if not checker.passed:
                # Fail closed: discard automated work, do NOT connect.
                if worktree is not None:
                    worktree.cleanup()
                    worktree = None
                ctx.log_stage("connector", "skip", "skipped (checker failed)")
                hr = _human_report(iteration, findings, maker_result, checker, None, "failed")
                return ctx.finalize("failed", findings_count=len(findings),
                                    changes_count=len(maker_result.changes),
                                    checker_passed=False, human_report=hr)

            # --- CONNECTOR -------------------------------------------------
            summary = {
                "run_id": ctx.run_id,
                "iteration": iteration,
                "status": "success",
                "findings_count": len(findings),
                "changes_count": len(maker_result.changes),
                "checker_passed": True,
                "changes": [c.to_dict() for c in maker_result.changes],
                "findings": [f.to_dict() for f in findings],
            }
            hr = _human_report(iteration, findings, maker_result, checker, None, "success")
            summary["human_report"] = hr
            connector = self._connector_instance()
            connector_result = connector.report(summary, worktree)
            ctx.log_stage("connector", "ok",
                          f"pushed={connector_result.pushed} "
                          f"pr={connector_result.created_pr} "
                          f"dry_run={connector_result.dry_run}")

            return ctx.finalize("success", findings_count=len(findings),
                                changes_count=len(maker_result.changes),
                                checker_passed=True,
                                human_report=hr)

        except Exception as exc:
            ctx.add_error(str(exc))
            ctx.log_stage("spine", "fail", str(exc))
            if worktree is not None:
                try:
                    worktree.cleanup()
                except Exception:  # pragma: no cover - best effort cleanup
                    pass
            return ctx.finalize("failed", findings_count=0,
                                changes_count=(len(maker_result.changes) if maker_result else 0),
                                checker_passed=(checker.passed if checker else None),
                                human_report=_human_report(iteration, [], maker_result, checker, connector_result, "failed"))
        finally:
            # Always discard a copy worktree at the end of a successful run.
            if worktree is not None and getattr(worktree, "_branch", None) is None:
                try:
                    worktree.cleanup()
                except Exception:  # pragma: no cover
                    pass
