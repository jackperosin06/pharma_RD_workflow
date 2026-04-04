"""CLI trigger (story 1.5)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pharma_rd.main import main_exit_code


def test_pharma_rd_run_prints_summary_json_last_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "app.db"
    art = tmp_path / "artifacts"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(art))
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "run"])

    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    rc = main_exit_code()
    assert rc == 0

    out = capsys.readouterr().out
    lines = [ln for ln in out.strip().split("\n") if ln.strip()]
    summary = json.loads(lines[-1])
    assert "run_id" in summary
    assert summary["poll_status"] == f"GET /runs/{summary['run_id']}"

    import sqlite3

    row = sqlite3.connect(db).execute(
        "SELECT status, run_id FROM runs WHERE run_id = ?",
        (summary["run_id"],),
    ).fetchone()
    assert row is not None
    assert row[0] == "completed"


def test_pharma_rd_run_failure_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "e.db"
    art = tmp_path / "a"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(art))
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "run"])

    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    def boom(*_args, **_kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr("pharma_rd.pipeline.runner.competitor.run_competitor", boom)

    rc = main_exit_code()
    assert rc == 1


def test_pharma_rd_no_args_prints_help(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["pharma-rd"])
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage:" in out.lower() or "run" in out
