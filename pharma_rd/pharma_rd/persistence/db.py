"""SQLite connection, schema migration, and retention purge."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

CURRENT_SCHEMA_VERSION = 2


def _parse_utc_iso(created_at: str) -> datetime:
    """Parse `runs.created_at` written by the app (`datetime.now(UTC).isoformat()`).

    Rejects malformed values so purge cannot mis-delete rows.
    """
    s = created_at.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt


_DDL_V1 = """
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    stage_key TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs (run_id) ON DELETE CASCADE,
    UNIQUE (run_id, stage_key)
);

CREATE INDEX idx_stages_run_id ON stages (run_id);
"""

_DDL_V2 = """
CREATE TABLE stage_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    stage_key TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    sha256_hex TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs (run_id) ON DELETE CASCADE,
    UNIQUE (run_id, stage_key)
);

CREATE INDEX idx_stage_artifacts_run_id ON stage_artifacts (run_id);
"""


def migrate(conn: sqlite3.Connection) -> None:
    """Apply DDL until `PRAGMA user_version` matches `CURRENT_SCHEMA_VERSION`."""
    row = conn.execute("PRAGMA user_version").fetchone()
    assert row is not None
    v: int = row[0]
    if v < 1:
        conn.executescript(_DDL_V1)
        conn.execute("PRAGMA user_version = 1")
        v = 1
    if v < 2:
        conn.executescript(_DDL_V2)
        conn.execute("PRAGMA user_version = 2")
        v = 2
    if v != CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {v} is not supported "
            f"(expected {CURRENT_SCHEMA_VERSION})"
        )
    conn.commit()


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Open SQLite, enable foreign keys, create parent dirs, run migrations."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


@contextmanager
def connection(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def purge_runs_older_than(conn: sqlite3.Connection, *, retention_days: int) -> int:
    """Delete runs (and cascaded stages) older than the retention window.

    Compares each row's `created_at` by parsing ISO8601 to UTC `datetime` objects.
    Rows must contain timestamps produced by this app (see `RunRepository` /
    migration) so parsing stays reliable; arbitrary hand-edited strings may raise
    `ValueError`.
    """
    if retention_days < 0:
        raise ValueError("retention_days must be non-negative")
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    rows = conn.execute("SELECT run_id, created_at FROM runs").fetchall()
    to_delete: list[str] = []
    for row in rows:
        rid, created_s = row["run_id"], row["created_at"]
        try:
            dt = _parse_utc_iso(created_s)
        except (TypeError, ValueError) as e:
            raise ValueError(
                "runs.created_at must be parseable ISO8601 UTC from the app: "
                f"{created_s!r}"
            ) from e
        if dt < cutoff:
            to_delete.append(rid)
    if not to_delete:
        return 0
    placeholders = ",".join("?" * len(to_delete))
    cur = conn.execute(f"DELETE FROM runs WHERE run_id IN ({placeholders})", to_delete)
    conn.commit()
    return cur.rowcount
