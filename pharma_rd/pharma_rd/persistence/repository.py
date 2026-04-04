"""Create and update pipeline run and stage rows."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

RUN_STATUSES = frozenset(
    {"pending", "running", "completed", "failed", "partial_failed"}
)
STAGE_STATUSES = frozenset({"pending", "running", "completed", "failed"})
_TERMINAL_STAGE = frozenset({"completed", "failed"})


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _require_run_status(status: str) -> None:
    if status not in RUN_STATUSES:
        raise ValueError(
            f"invalid run status {status!r}; expected one of {sorted(RUN_STATUSES)}"
        )


def _require_stage_status(status: str) -> None:
    if status not in STAGE_STATUSES:
        raise ValueError(
            f"invalid stage status {status!r}; expected one of {sorted(STAGE_STATUSES)}"
        )


class RunRepository:
    """Persistence API for runs and stages (stdlib sqlite3 only)."""

    def create_run(
        self,
        conn: sqlite3.Connection,
        *,
        initial_status: str = "pending",
        run_id: str | None = None,
    ) -> str:
        _require_run_status(initial_status)
        rid = run_id or str(uuid.uuid4())
        now = _utc_now_iso()
        try:
            conn.execute(
                """
                INSERT INTO runs (run_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (rid, initial_status, now, now),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError(f"run_id already exists: {rid!r}") from e
        conn.commit()
        return rid

    def update_run_status(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        status: str,
    ) -> None:
        _require_run_status(status)
        now = _utc_now_iso()
        cur = conn.execute(
            """
            UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ?
            """,
            (status, now, run_id),
        )
        if cur.rowcount != 1:
            raise KeyError(f"run not found: {run_id}")
        conn.commit()

    def upsert_stage(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        stage_key: str,
        status: str,
    ) -> None:
        _require_stage_status(status)
        if not stage_key.strip():
            raise ValueError("stage_key must be non-empty")
        now = _utc_now_iso()
        row = conn.execute(
            """
            SELECT started_at, ended_at, status FROM stages
            WHERE run_id = ? AND stage_key = ?
            """,
            (run_id, stage_key),
        ).fetchone()
        if row is None:
            started_at = now if status == "running" else None
            ended_at = now if status in ("completed", "failed") else None
            conn.execute(
                """
                INSERT INTO stages (
                    run_id, stage_key, status, started_at, ended_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, stage_key, status, started_at, ended_at, now),
            )
        else:
            prev_status = row["status"]
            started_at, ended_at = row["started_at"], row["ended_at"]
            leaving_terminal = (
                prev_status in _TERMINAL_STAGE and status not in _TERMINAL_STAGE
            )
            if leaving_terminal:
                if status == "pending":
                    started_at = None
                    ended_at = None
                elif status == "running":
                    started_at = now
                    ended_at = None
            else:
                if status == "running" and started_at is None:
                    started_at = now
                if status in _TERMINAL_STAGE:
                    ended_at = now
            conn.execute(
                """
                UPDATE stages
                SET status = ?, updated_at = ?, started_at = ?, ended_at = ?
                WHERE run_id = ? AND stage_key = ?
                """,
                (status, now, started_at, ended_at, run_id, stage_key),
            )
        conn.commit()
