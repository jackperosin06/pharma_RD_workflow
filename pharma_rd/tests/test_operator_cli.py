"""Operator CLI: runs list and per-run status (story 1.6)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pharma_rd.main import main_exit_code
from pharma_rd.operator_queries import get_run_with_stages, list_runs
from pharma_rd.persistence import connect
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline.order import PIPELINE_ORDER


def test_list_runs_empty_db_captured(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "o.db"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "runs"])
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    main_exit_code()
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data == {"runs": []}
    from pharma_rd.config import get_settings as gs

    gs.cache_clear()


def test_list_runs_limit_and_order(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "o.db"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    conn = connect(db)
    repo = RunRepository()
    repo.create_run(conn, initial_status="completed")
    r2 = repo.create_run(conn, initial_status="failed")
    conn.close()

    monkeypatch.setattr(sys, "argv", ["pharma-rd", "runs", "--limit", "1"])
    get_settings.cache_clear()
    main_exit_code()
    data = json.loads(capsys.readouterr().out.strip())
    assert len(data["runs"]) == 1
    # Newest first: r2 should win
    assert data["runs"][0]["run_id"] == r2
    for k in ("run_id", "status", "created_at", "updated_at"):
        assert k in data["runs"][0]
    get_settings.cache_clear()


def test_status_unknown_run_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "o.db"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    monkeypatch.setattr(
        sys,
        "argv",
        ["pharma-rd", "status", "00000000-0000-0000-0000-000000000000"],
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc != 0
    err = capsys.readouterr().err
    assert "not found" in err.lower()
    assert "traceback" not in err.lower()
    get_settings.cache_clear()


def test_status_pipeline_order_and_error_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "o.db"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn, initial_status="failed")
    repo.update_run_status(conn, rid, "failed")
    repo.upsert_stage(conn, rid, "clinical", "completed")
    repo.upsert_stage(
        conn,
        rid,
        "competitor",
        "failed",
        error_summary="RuntimeError: boom",
    )
    conn.close()

    monkeypatch.setattr(sys, "argv", ["pharma-rd", "status", rid])
    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 0
    data = json.loads(capsys.readouterr().out.strip())
    assert data["run"]["run_id"] == rid
    assert data["run"]["status"] == "failed"
    keys = [s["stage_key"] for s in data["stages"]]
    assert keys == sorted(keys, key=lambda k: PIPELINE_ORDER.index(k))
    comp = next(s for s in data["stages"] if s["stage_key"] == "competitor")
    assert comp["status"] == "failed"
    assert comp["error_summary"] == "RuntimeError: boom"
    get_settings.cache_clear()


def test_list_runs_helper_rejects_non_positive_limit(tmp_path: Path) -> None:
    conn = connect(tmp_path / "x.db")
    try:
        with pytest.raises(ValueError, match="at least 1"):
            list_runs(conn, limit=0)
    finally:
        conn.close()


def test_get_run_with_stages_none(tmp_path: Path) -> None:
    conn = connect(tmp_path / "mem.db")
    try:
        assert get_run_with_stages(conn, "nope") is None
    finally:
        conn.close()
