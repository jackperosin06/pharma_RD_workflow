"""Tests for SQLite run/stage persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pharma_rd.persistence import (
    CURRENT_SCHEMA_VERSION,
    connect,
    migrate,
    purge_runs_older_than,
)
from pharma_rd.persistence.repository import RunRepository


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "a.db"
    c1 = connect(db)
    v1 = c1.execute("PRAGMA user_version").fetchone()[0]
    assert v1 == CURRENT_SCHEMA_VERSION
    c1.close()
    c2 = connect(db)
    v2 = c2.execute("PRAGMA user_version").fetchone()[0]
    assert v2 == CURRENT_SCHEMA_VERSION
    c2.close()


def test_migrate_on_existing_connection(tmp_path: Path) -> None:
    db = tmp_path / "b.db"
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    conn.close()
    conn2 = connect(db)
    assert conn2.execute("PRAGMA user_version").fetchone()[0] == CURRENT_SCHEMA_VERSION
    conn2.close()


def test_create_run_upsert_stage_and_update_run(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "c.db")
    rid = repo.create_run(conn, initial_status="pending")
    assert len(rid) == 36
    repo.update_run_status(conn, rid, "running")
    repo.upsert_stage(conn, rid, "clinical", "pending")
    repo.upsert_stage(conn, rid, "clinical", "running")
    repo.upsert_stage(conn, rid, "clinical", "completed")
    row = conn.execute(
        """
        SELECT status, started_at IS NOT NULL, ended_at IS NOT NULL
        FROM stages WHERE run_id = ?
        """,
        (rid,),
    ).fetchone()
    assert row[0] == "completed"
    assert row[1] == 1
    assert row[2] == 1
    repo.update_run_status(conn, rid, "completed")
    conn.close()


def test_purge_removes_old_runs(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "d.db")
    old_id = repo.create_run(conn, initial_status="completed")
    conn.execute(
        "UPDATE runs SET created_at = ? WHERE run_id = ?",
        ("2000-01-01T00:00:00+00:00", old_id),
    )
    conn.commit()
    new_id = repo.create_run(conn, initial_status="pending")
    conn.execute(
        "UPDATE runs SET created_at = ? WHERE run_id = ?",
        ("2099-01-01T00:00:00+00:00", new_id),
    )
    conn.commit()
    repo.upsert_stage(conn, old_id, "s", "completed")
    repo.upsert_stage(conn, new_id, "s", "pending")
    n = purge_runs_older_than(conn, retention_days=30)
    assert n == 1
    remaining = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    assert remaining == 1
    stages = conn.execute("SELECT COUNT(*) FROM stages").fetchone()[0]
    assert stages == 1
    conn.close()


def test_stage_requires_parent_run(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "e.db")
    with pytest.raises(sqlite3.IntegrityError):
        repo.upsert_stage(conn, "00000000-0000-0000-0000-000000000000", "x", "pending")
    conn.close()


def test_invalid_status_raises(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "f.db")
    with pytest.raises(ValueError, match="invalid run status"):
        repo.create_run(conn, initial_status="bogus")
    rid = repo.create_run(conn)
    with pytest.raises(ValueError, match="invalid stage status"):
        repo.upsert_stage(conn, rid, "k", "bogus")
    conn.close()


def test_duplicate_explicit_run_id_raises(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "g.db")
    fixed = "11111111-1111-1111-1111-111111111111"
    repo.create_run(conn, run_id=fixed)
    with pytest.raises(ValueError, match="run_id already exists"):
        repo.create_run(conn, run_id=fixed)
    conn.close()


def test_empty_stage_key_raises(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "h.db")
    rid = repo.create_run(conn)
    with pytest.raises(ValueError, match="non-empty"):
        repo.upsert_stage(conn, rid, "   ", "pending")
    conn.close()


def test_stage_retry_after_completed_clears_ended_at(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "i.db")
    rid = repo.create_run(conn)
    repo.upsert_stage(conn, rid, "clinical", "running")
    repo.upsert_stage(conn, rid, "clinical", "completed")
    ended_before = conn.execute(
        "SELECT ended_at FROM stages WHERE run_id = ?", (rid,)
    ).fetchone()[0]
    assert ended_before is not None
    repo.upsert_stage(conn, rid, "clinical", "running")
    row = conn.execute(
        "SELECT status, ended_at FROM stages WHERE run_id = ?", (rid,)
    ).fetchone()
    assert row[0] == "running"
    assert row[1] is None
    conn.close()


def test_purge_invalid_created_at_raises(tmp_path: Path) -> None:
    repo = RunRepository()
    conn = connect(tmp_path / "j.db")
    rid = repo.create_run(conn)
    conn.execute(
        "UPDATE runs SET created_at = ? WHERE run_id = ?",
        ("not-a-date", rid),
    )
    conn.commit()
    with pytest.raises(ValueError, match="parseable"):
        purge_runs_older_than(conn, retention_days=30)
    conn.close()
