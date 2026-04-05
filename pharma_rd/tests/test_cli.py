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


def test_pharma_rd_invalid_therapeutic_areas_exits_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PHARMA_RD_THERAPEUTIC_AREAS", "bad&label")
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "runs"])

    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    from pharma_rd.main import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "THERAPEUTIC" in err.upper() or "validation" in err.lower()


def test_pharma_rd_invalid_pubmed_base_exits_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PHARMA_RD_PUBMED_EUTILS_BASE", ":::")
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "runs"])

    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    from pharma_rd.main import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "PUBMED" in err.upper() or "validation" in err.lower()


def test_pharma_rd_invalid_competitor_watchlist_exits_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PHARMA_RD_COMPETITOR_WATCHLIST", "bad;label")
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "runs"])

    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    from pharma_rd.main import main

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "COMPETITOR" in err.upper() or "validation" in err.lower()


def test_cli_runs_denied_when_guard_without_cli_token(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "g.db"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(tmp_path / "ga"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "expected-secret")
    monkeypatch.delenv("PHARMA_RD_CLI_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "runs"])
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 1
    assert "access denied" in capsys.readouterr().err.lower()


def test_cli_runs_ok_when_cli_token_matches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "h.db"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(tmp_path / "ha"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "expected-secret")
    monkeypatch.setenv("PHARMA_RD_CLI_ACCESS_TOKEN", "expected-secret")
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "runs"])
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 0
    out = capsys.readouterr().out
    assert '"runs"' in out or "runs" in out


def test_cli_run_denied_when_guard_without_cli_token(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "i.db"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(tmp_path / "ia"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "expected-secret")
    monkeypatch.delenv("PHARMA_RD_CLI_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "run"])
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 1
    assert "access denied" in capsys.readouterr().err.lower()


def test_cli_status_denied_when_guard_without_cli_token(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "s.db"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(tmp_path / "sa"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "expected-secret")
    monkeypatch.delenv("PHARMA_RD_CLI_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["pharma-rd", "status", "00000000-0000-4000-8000-000000000001"],
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 1
    assert "access denied" in capsys.readouterr().err.lower()


def test_cli_status_ok_when_cli_token_matches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "t.db"
    art = tmp_path / "ta"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(art))
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "expected-secret")
    monkeypatch.setenv("PHARMA_RD_CLI_ACCESS_TOKEN", "expected-secret")

    from pharma_rd.config import get_settings
    from pharma_rd.persistence import connect
    from pharma_rd.persistence.repository import RunRepository

    get_settings.cache_clear()
    conn = connect(db)
    try:
        rid = RunRepository().create_run(conn)
    finally:
        conn.close()

    monkeypatch.setattr(sys, "argv", ["pharma-rd", "status", rid])
    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["run"]["run_id"] == rid


def test_cli_retry_stage_denied_when_guard_without_cli_token(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "r.db"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(tmp_path / "ra"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "expected-secret")
    monkeypatch.delenv("PHARMA_RD_CLI_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pharma-rd",
            "retry-stage",
            "00000000-0000-4000-8000-000000000002",
            "clinical",
        ],
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    rc = main_exit_code()
    assert rc == 1
    assert "access denied" in capsys.readouterr().err.lower()


def test_cli_retry_stage_ok_when_cli_token_matches(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "u.db"
    art = tmp_path / "ua"
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(db))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(art))
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "expected-secret")
    monkeypatch.setenv("PHARMA_RD_CLI_ACCESS_TOKEN", "expected-secret")
    rid = "00000000-0000-4000-8000-000000000003"
    monkeypatch.setattr(sys, "argv", ["pharma-rd", "retry-stage", rid, "clinical"])

    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    def _noop_validate(*_a: object, **_k: object) -> None:
        return None

    def _noop_resume(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr("pharma_rd.cli.validate_stage_retry", _noop_validate)
    monkeypatch.setattr("pharma_rd.cli.run_pipeline_resume_from", _noop_resume)

    rc = main_exit_code()
    assert rc == 0
    out = capsys.readouterr().out
    summary = json.loads(out.strip())
    assert summary["run_id"] == rid
    assert summary["resumed_from"] == "clinical"


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
