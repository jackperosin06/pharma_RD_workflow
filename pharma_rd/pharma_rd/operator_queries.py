"""Read-only queries for operator CLI (runs list, per-run stage status)."""

from __future__ import annotations

import sqlite3
from typing import Any

from pharma_rd.pipeline.order import PIPELINE_ORDER

_STAGE_ORDER = {k: i for i, k in enumerate(PIPELINE_ORDER)}


def list_runs(conn: sqlite3.Connection, *, limit: int) -> list[dict[str, Any]]:
    """Recent runs, newest first (`created_at` DESC)."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    rows = conn.execute(
        """
        SELECT run_id, status, created_at, updated_at
        FROM runs
        ORDER BY created_at DESC, run_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "run_id": r["run_id"],
            "status": r["status"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def get_run_with_stages(
    conn: sqlite3.Connection, run_id: str
) -> dict[str, Any] | None:
    """Single run plus stages, sorted in pipeline order."""
    run_row = conn.execute(
        """
        SELECT run_id, status, created_at, updated_at
        FROM runs WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if run_row is None:
        return None
    run = {
        "run_id": run_row["run_id"],
        "status": run_row["status"],
        "created_at": run_row["created_at"],
        "updated_at": run_row["updated_at"],
    }
    stage_rows = conn.execute(
        """
        SELECT stage_key, status, started_at, ended_at, error_summary
        FROM stages WHERE run_id = ?
        """,
        (run_id,),
    ).fetchall()
    stages: list[dict[str, Any]] = []
    for r in stage_rows:
        stages.append(
            {
                "stage_key": r["stage_key"],
                "status": r["status"],
                "started_at": r["started_at"],
                "ended_at": r["ended_at"],
                "error_summary": r["error_summary"],
            }
        )
    stages.sort(
        key=lambda s: (_STAGE_ORDER.get(s["stage_key"], 10_000), s["stage_key"])
    )
    return {"run": run, "stages": stages}
