"""In-process pipeline runner: ordered stages, artifact handoffs, DB updates.

Linear handoff graph (Epic 2+ retries may reuse this map):

    clinical -> competitor -> consumer -> synthesis -> delivery

Each stage after ``clinical`` loads the previous stage's JSON artifact from disk,
validates with Pydantic, then runs the stub agent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from pydantic import BaseModel

from pharma_rd.agents import clinical, competitor, consumer, delivery, synthesis
from pharma_rd.config import get_settings
from pharma_rd.http_client import ConnectorFailure
from pharma_rd.logging_setup import (
    configure_pipeline_logging,
    get_pipeline_logger,
    pipeline_run_logging,
    stage_logging,
)
from pharma_rd.persistence.artifacts import (
    read_artifact_bytes,
    read_stage_artifact_model,
    write_stage_artifact,
)
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerOutput,
    SynthesisOutput,
)
from pharma_rd.pipeline.order import PIPELINE_ORDER

_log = get_pipeline_logger("pharma_rd.pipeline.runner")


def _write_artifact_with_replacement_log(
    conn: sqlite3.Connection,
    artifact_root: Path,
    run_id: str,
    stage_key: str,
    model: BaseModel,
    repo: RunRepository,
) -> None:
    """Persist artifact; log when SHA-256 changes (NFR-R3 / story 2.3)."""
    old = repo.get_stage_artifact_sha256(conn, run_id, stage_key)
    rec = write_stage_artifact(
        conn,
        artifact_root=artifact_root,
        run_id=run_id,
        stage_key=stage_key,
        model=model,
    )
    if old is not None and old != rec.sha256_hex:
        _log.info(
            "stage artifact replaced",
            extra={
                "event": "stage_artifact_replaced",
                "outcome": "ok",
                "stage": stage_key,
                "previous_sha256": old,
                "new_sha256": rec.sha256_hex,
            },
        )


def _execute_stage(
    conn: sqlite3.Connection,
    artifact_root: Path,
    run_id: str,
    stage_key: str,
    repo: RunRepository,
    *,
    resume_context: bool = False,
) -> None:
    """Run a single stage: running → agent → artifact → completed."""
    with stage_logging(stage_key):
        if resume_context:
            _log.info(
                "stage retry",
                extra={"event": "stage_retry", "outcome": None},
            )
        repo.upsert_stage(conn, run_id, stage_key, "running")
        _log.info(
            "stage running",
            extra={"event": "stage_started", "outcome": None},
        )
        if stage_key == "clinical":
            out: BaseModel = clinical.run_clinical(run_id)
        elif stage_key == "competitor":
            prev = ClinicalOutput.model_validate_json(
                read_artifact_bytes(artifact_root, run_id, "clinical")
            )
            out = competitor.run_competitor(run_id, prev)
        elif stage_key == "consumer":
            prev2 = CompetitorOutput.model_validate_json(
                read_artifact_bytes(artifact_root, run_id, "competitor")
            )
            out = consumer.run_consumer(run_id, prev2)
        elif stage_key == "synthesis":
            clin = read_stage_artifact_model(
                artifact_root, run_id, "clinical", ClinicalOutput
            )
            comp = read_stage_artifact_model(
                artifact_root, run_id, "competitor", CompetitorOutput
            )
            cons = read_stage_artifact_model(
                artifact_root, run_id, "consumer", ConsumerOutput
            )
            out = synthesis.run_synthesis(run_id, clin, comp, cons)
        elif stage_key == "delivery":
            prev4 = SynthesisOutput.model_validate_json(
                read_artifact_bytes(artifact_root, run_id, "synthesis")
            )
            out = delivery.run_delivery(run_id, prev4, artifact_root)
        else:
            raise ValueError(f"unknown stage_key: {stage_key!r}")

        _write_artifact_with_replacement_log(
            conn, artifact_root, run_id, stage_key, out, repo
        )
        repo.upsert_stage(conn, run_id, stage_key, "completed")
        _log.info(
            "stage finished",
            extra={"event": "stage_completed", "outcome": "completed"},
        )


def _handle_pipeline_failure(
    conn: sqlite3.Connection,
    run_id: str,
    stage_key: str,
    repo: RunRepository,
    e: Exception,
    *,
    completed_in_invocation: int,
    prior_upstream_completed: int,
) -> None:
    err_extras: dict[str, object] = {
        "event": "stage_failed",
        "outcome": "failed",
        "stage": stage_key,
        "agent": stage_key,
        "error_type": type(e).__name__,
    }
    if isinstance(e, ConnectorFailure):
        err_extras["integration_error_class"] = e.error_class.value
    _log.error(
        "stage failed",
        extra=err_extras,
    )
    if isinstance(e, ConnectorFailure):
        err_summary = f"{type(e).__name__} [{e.error_class.value}]: {e}"
    else:
        err_summary = f"{type(e).__name__}: {e}"
    repo.upsert_stage(
        conn,
        run_id,
        stage_key,
        "failed",
        error_summary=err_summary,
    )
    total_done = prior_upstream_completed + completed_in_invocation
    run_status = "partial_failed" if total_done > 0 else "failed"
    repo.update_run_status(conn, run_id, run_status)
    _log.error(
        "pipeline run finished with failure",
        extra={
            "event": "run_failed",
            "outcome": run_status,
            "completed_stage_count": total_done,
            "run_status": run_status,
        },
    )


def run_pipeline(
    conn: sqlite3.Connection,
    *,
    artifact_root: Path,
    run_id: str,
    repo: RunRepository | None = None,
) -> None:
    """Execute all stages in order for ``run_id``; update run + stage rows.

    On success: run status ``completed``. On failure: failing stage ``failed``;
    run ``failed`` if no stage completed, else ``partial_failed``.
    """
    configure_pipeline_logging()
    repo = repo or RunRepository()
    prior_upstream_completed = 0
    with pipeline_run_logging(run_id):
        _settings = get_settings()
        _log.info(
            "pipeline run started",
            extra={
                "event": "run_started",
                "outcome": None,
                "deployment_profile": _settings.deployment_profile,
            },
        )
        repo.update_run_status(conn, run_id, "running")
        completed = 0
        stage_key: str = PIPELINE_ORDER[0]

        try:
            for stage_key in PIPELINE_ORDER:
                _execute_stage(
                    conn,
                    artifact_root,
                    run_id,
                    stage_key,
                    repo,
                    resume_context=False,
                )
                completed += 1

            repo.update_run_status(conn, run_id, "completed")
            _log.info(
                "pipeline run finished",
                extra={
                    "event": "run_completed",
                    "outcome": "completed",
                    "completed_stage_count": prior_upstream_completed + completed,
                    "run_status": "completed",
                },
            )
        except Exception as e:
            try:
                _handle_pipeline_failure(
                    conn,
                    run_id,
                    stage_key,
                    repo,
                    e,
                    completed_in_invocation=completed,
                    prior_upstream_completed=prior_upstream_completed,
                )
            except Exception as cleanup_err:
                raise cleanup_err from e
            raise


def run_pipeline_resume_from(
    conn: sqlite3.Connection,
    *,
    artifact_root: Path,
    run_id: str,
    start_stage_key: str,
    repo: RunRepository | None = None,
) -> None:
    """Resume from ``start_stage_key`` through delivery; upstream must exist on disk."""
    configure_pipeline_logging()
    repo = repo or RunRepository()
    if start_stage_key not in PIPELINE_ORDER:
        raise ValueError(f"unknown start_stage_key: {start_stage_key!r}")
    start_idx = PIPELINE_ORDER.index(start_stage_key)
    prior_upstream_completed = start_idx

    with pipeline_run_logging(run_id):
        _settings = get_settings()
        _log.info(
            "pipeline resume started",
            extra={
                "event": "pipeline_resume",
                "outcome": None,
                "resumed_from_stage": start_stage_key,
                "deployment_profile": _settings.deployment_profile,
            },
        )
        repo.update_run_status(conn, run_id, "running")
        completed = 0
        slice_keys = PIPELINE_ORDER[start_idx:]
        stage_key: str = start_stage_key

        try:
            for stage_key in slice_keys:
                _execute_stage(
                    conn,
                    artifact_root,
                    run_id,
                    stage_key,
                    repo,
                    resume_context=True,
                )
                completed += 1

            repo.update_run_status(conn, run_id, "completed")
            _log.info(
                "pipeline run finished",
                extra={
                    "event": "run_completed",
                    "outcome": "completed",
                    "completed_stage_count": prior_upstream_completed + completed,
                    "run_status": "completed",
                    "resumed_from_stage": start_stage_key,
                },
            )
        except Exception as e:
            try:
                _handle_pipeline_failure(
                    conn,
                    run_id,
                    stage_key,
                    repo,
                    e,
                    completed_in_invocation=completed,
                    prior_upstream_completed=prior_upstream_completed,
                )
            except Exception as cleanup_err:
                raise cleanup_err from e
            raise
