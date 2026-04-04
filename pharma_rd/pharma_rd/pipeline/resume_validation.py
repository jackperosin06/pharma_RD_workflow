"""Validate preconditions for ``retry-stage`` (story 2.3 / FR30)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from pharma_rd.pipeline.order import PIPELINE_ORDER

_RETRYABLE_RUN_STATUSES = frozenset({"failed", "partial_failed"})


def validate_stage_retry(
    conn: sqlite3.Connection,
    artifact_root: Path,
    run_id: str,
    stage_key: str,
) -> None:
    """Raise ``ValueError`` with an operator-safe message if retry is not allowed.

    Does not mutate the database.
    """
    if stage_key not in PIPELINE_ORDER:
        raise ValueError(f"unknown stage: {stage_key!r}")

    run_row = conn.execute(
        "SELECT status FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if run_row is None:
        raise ValueError(f"run not found: {run_id}")

    run_status = run_row["status"]
    if run_status == "completed":
        raise ValueError("run is already completed; nothing to retry")
    if run_status not in _RETRYABLE_RUN_STATUSES:
        raise ValueError(
            f"run status is {run_status!r}; expected failed or partial_failed"
        )

    idx = PIPELINE_ORDER.index(stage_key)
    st = conn.execute(
        """
        SELECT status FROM stages
        WHERE run_id = ? AND stage_key = ?
        """,
        (run_id, stage_key),
    ).fetchone()
    if st is None:
        raise ValueError(f"no stage row for {stage_key!r}; cannot retry")
    if st["status"] != "failed":
        raise ValueError(
            f"stage {stage_key!r} status is {st['status']!r}; expected failed"
        )

    for up in PIPELINE_ORDER[:idx]:
        ur = conn.execute(
            """
            SELECT status FROM stages
            WHERE run_id = ? AND stage_key = ?
            """,
            (run_id, up),
        ).fetchone()
        if ur is None or ur["status"] != "completed":
            raise ValueError(
                f"upstream stage {up!r} must be completed before retrying "
                f"{stage_key!r}"
            )
        art = artifact_root / run_id / up / "output.json"
        if not art.is_file():
            raise ValueError(
                f"missing artifact for upstream stage {up!r}: {art}",
            )
