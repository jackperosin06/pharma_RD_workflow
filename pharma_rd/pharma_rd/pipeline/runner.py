"""In-process pipeline runner: ordered stages, artifact handoffs, DB updates.

Linear handoff graph (Epic 2+ retries may reuse this map):

    clinical -> competitor -> consumer -> synthesis -> delivery

Each stage after ``clinical`` loads the previous stage's JSON artifact from disk,
validates with Pydantic, then runs the stub agent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from pharma_rd.agents import clinical, competitor, consumer, delivery, synthesis
from pharma_rd.persistence.artifacts import read_artifact_bytes, write_stage_artifact
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerOutput,
    SynthesisOutput,
)

# Fixed execution order (PRD / architecture).
PIPELINE_ORDER: tuple[str, ...] = (
    "clinical",
    "competitor",
    "consumer",
    "synthesis",
    "delivery",
)

# Previous stage key for each non-root stage (explicit wiring for operators / retries).
PIPELINE_EDGES: dict[str, str | None] = {
    "clinical": None,
    "competitor": "clinical",
    "consumer": "competitor",
    "synthesis": "consumer",
    "delivery": "synthesis",
}


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
    repo = repo or RunRepository()
    repo.update_run_status(conn, run_id, "running")
    completed = 0
    stage_key = "clinical"

    try:
        # clinical — no upstream
        repo.upsert_stage(conn, run_id, stage_key, "running")
        out = clinical.run_clinical(run_id)
        write_stage_artifact(
            conn,
            artifact_root=artifact_root,
            run_id=run_id,
            stage_key=stage_key,
            model=out,
        )
        repo.upsert_stage(conn, run_id, stage_key, "completed")
        completed += 1

        # competitor
        stage_key = "competitor"
        repo.upsert_stage(conn, run_id, stage_key, "running")
        prev = ClinicalOutput.model_validate_json(
            read_artifact_bytes(artifact_root, run_id, "clinical")
        )
        out2 = competitor.run_competitor(run_id, prev)
        write_stage_artifact(
            conn,
            artifact_root=artifact_root,
            run_id=run_id,
            stage_key=stage_key,
            model=out2,
        )
        repo.upsert_stage(conn, run_id, stage_key, "completed")
        completed += 1

        # consumer
        stage_key = "consumer"
        repo.upsert_stage(conn, run_id, stage_key, "running")
        prev2 = CompetitorOutput.model_validate_json(
            read_artifact_bytes(artifact_root, run_id, "competitor")
        )
        out3 = consumer.run_consumer(run_id, prev2)
        write_stage_artifact(
            conn,
            artifact_root=artifact_root,
            run_id=run_id,
            stage_key=stage_key,
            model=out3,
        )
        repo.upsert_stage(conn, run_id, stage_key, "completed")
        completed += 1

        # synthesis
        stage_key = "synthesis"
        repo.upsert_stage(conn, run_id, stage_key, "running")
        prev3 = ConsumerOutput.model_validate_json(
            read_artifact_bytes(artifact_root, run_id, "consumer")
        )
        out4 = synthesis.run_synthesis(run_id, prev3)
        write_stage_artifact(
            conn,
            artifact_root=artifact_root,
            run_id=run_id,
            stage_key=stage_key,
            model=out4,
        )
        repo.upsert_stage(conn, run_id, stage_key, "completed")
        completed += 1

        # delivery
        stage_key = "delivery"
        repo.upsert_stage(conn, run_id, stage_key, "running")
        prev4 = SynthesisOutput.model_validate_json(
            read_artifact_bytes(artifact_root, run_id, "synthesis")
        )
        out5 = delivery.run_delivery(run_id, prev4)
        write_stage_artifact(
            conn,
            artifact_root=artifact_root,
            run_id=run_id,
            stage_key=stage_key,
            model=out5,
        )
        repo.upsert_stage(conn, run_id, stage_key, "completed")
        completed += 1

        repo.update_run_status(conn, run_id, "completed")
    except Exception as e:
        try:
            repo.upsert_stage(conn, run_id, stage_key, "failed")
            repo.update_run_status(
                conn,
                run_id,
                "partial_failed" if completed > 0 else "failed",
            )
        except Exception as cleanup_err:
            raise cleanup_err from e
        raise
