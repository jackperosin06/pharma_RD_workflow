"""On-demand pipeline trigger (CLI) — story 1.5 / FR1; operator queries — story 1.6."""

from __future__ import annotations

import json
import sys

from pharma_rd.access_control import cli_access_exit_code
from pharma_rd.config import get_settings
from pharma_rd.operator_queries import get_run_with_stages, list_runs
from pharma_rd.persistence import connect
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline import run_pipeline, run_pipeline_resume_from
from pharma_rd.pipeline.resume_validation import validate_stage_retry


def execute_pipeline_run(
    *,
    emit_summary_json: bool = True,
    enforce_cli_access: bool = True,
) -> int:
    """Create a run and execute the full pipeline (shared by ``run`` and scheduler).

    When ``emit_summary_json`` is False (scheduled runs), no summary JSON line is
    printed to stdout — structured logs from ``run_pipeline`` remain the trace.

    ``enforce_cli_access``: when True and ``artifact_access_token`` is set, require
    ``PHARMA_RD_CLI_ACCESS_TOKEN`` (FR32). Set False for in-process scheduled runs.
    """
    if enforce_cli_access:
        denied = cli_access_exit_code()
        if denied is not None:
            return denied
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        repo = RunRepository()
        run_id = repo.create_run(conn)
        run_pipeline(
            conn,
            artifact_root=settings.artifacts_root,
            run_id=run_id,
        )
    except Exception as e:
        print(f"pharma_rd run failed: {e}", file=sys.stderr)
        return 1
    else:
        if emit_summary_json:
            summary = {
                "run_id": run_id,
                "poll_status": f"GET /runs/{run_id}",
            }
            print(json.dumps(summary, ensure_ascii=False))
        return 0
    finally:
        conn.close()


def run_foreground_pipeline() -> int:
    """Create a run, execute the full pipeline, print one summary JSON line on success.

    Structured logs (story 1.4) are emitted to stdout first; the **last** line of stdout
    is the summary object (``run_id``, ``poll_status``) for scripts and operators.
    """
    return execute_pipeline_run(emit_summary_json=True)


def cmd_runs(*, limit: int) -> int:
    """Print one JSON object: `{"runs": [...]}` for operators and scripts (FR29)."""
    denied = cli_access_exit_code()
    if denied is not None:
        return denied
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        runs = list_runs(conn, limit=limit)
        print(json.dumps({"runs": runs}, ensure_ascii=False))
        return 0
    finally:
        conn.close()


def cmd_retry_stage(run_id: str, stage_key: str) -> int:
    """Resume a failed run from ``stage_key`` (FR30 / story 2.3)."""
    denied = cli_access_exit_code()
    if denied is not None:
        return denied
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        try:
            validate_stage_retry(conn, settings.artifacts_root, run_id, stage_key)
        except ValueError as e:
            print(f"retry-stage: {e}", file=sys.stderr)
            return 2
        try:
            run_pipeline_resume_from(
                conn,
                artifact_root=settings.artifacts_root,
                run_id=run_id,
                start_stage_key=stage_key,
            )
        except Exception as e:
            print(f"pharma_rd retry-stage failed: {e}", file=sys.stderr)
            return 1
        summary = {
            "run_id": run_id,
            "poll_status": f"GET /runs/{run_id}",
            "resumed_from": stage_key,
        }
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    finally:
        conn.close()


def cmd_status(run_id: str) -> int:
    """Print one JSON object with `run` and `stages` (per-agent status, FR31)."""
    denied = cli_access_exit_code()
    if denied is not None:
        return denied
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        payload = get_run_with_stages(conn, run_id)
        if payload is None:
            print(f"run not found: {run_id}", file=sys.stderr)
            return 2
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    finally:
        conn.close()
