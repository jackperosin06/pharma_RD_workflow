"""Tests for resume-from-stage (story 2.3 / FR30)."""

from __future__ import annotations

import pytest
from pharma_rd.config import get_settings
from pharma_rd.persistence import connect
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline import run_pipeline, run_pipeline_resume_from
from pharma_rd.pipeline.contracts import ClinicalOutput, CompetitorOutput
from pharma_rd.pipeline.order import PIPELINE_ORDER
from pharma_rd.pipeline.resume_validation import validate_stage_retry


@pytest.fixture(autouse=True)
def _clear_connector_probe_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset connector probe env; ``get_settings()`` cache is shared across tests."""
    monkeypatch.delenv("PHARMA_RD_CONNECTOR_PROBE_URL", raising=False)
    get_settings.cache_clear()


def test_validate_rejects_completed_run(tmp_path) -> None:
    db = tmp_path / "a.db"
    art = tmp_path / "art"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)
    run_pipeline(conn, artifact_root=art, run_id=rid)
    with pytest.raises(ValueError, match="already completed"):
        validate_stage_retry(conn, art, rid, "delivery")


def test_resume_from_rejects_unknown_start_stage(tmp_path) -> None:
    db = tmp_path / "u.db"
    art = tmp_path / "ar"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)
    with pytest.raises(ValueError, match="unknown start_stage_key"):
        run_pipeline_resume_from(
            conn,
            artifact_root=art,
            run_id=rid,
            start_stage_key="not-a-stage",
        )


def test_validate_rejects_unknown_stage(tmp_path) -> None:
    db = tmp_path / "b.db"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)
    with pytest.raises(ValueError, match="unknown stage"):
        validate_stage_retry(conn, tmp_path / "x", rid, "not-a-stage")


def test_retry_after_competitor_failure_completes_run(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "c.db"
    art = tmp_path / "artifacts"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)

    calls = {"n": 0}

    def flaky_competitor(rid_: str, clinical: ClinicalOutput) -> CompetitorOutput:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated competitor failure")
        return CompetitorOutput(run_id=rid_)

    monkeypatch.setattr(
        "pharma_rd.pipeline.runner.competitor.run_competitor",
        flaky_competitor,
    )

    with pytest.raises(RuntimeError, match="simulated"):
        run_pipeline(conn, artifact_root=art, run_id=rid)

    assert (
        conn.execute("SELECT status FROM runs WHERE run_id = ?", (rid,)).fetchone()[0]
        == "partial_failed"
    )
    comp = conn.execute(
        "SELECT status FROM stages WHERE run_id = ? AND stage_key = ?",
        (rid, "competitor"),
    ).fetchone()
    assert comp[0] == "failed"

    validate_stage_retry(conn, art, rid, "competitor")

    run_pipeline_resume_from(
        conn,
        artifact_root=art,
        run_id=rid,
        start_stage_key="competitor",
    )

    assert (
        conn.execute("SELECT status FROM runs WHERE run_id = ?", (rid,)).fetchone()[0]
        == "completed"
    )
    for sk in PIPELINE_ORDER:
        st = conn.execute(
            "SELECT status FROM stages WHERE run_id = ? AND stage_key = ?",
            (rid, sk),
        ).fetchone()
        assert st[0] == "completed"


def test_validate_rejects_when_target_stage_not_failed(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cannot retry ``clinical`` when it completed but a downstream stage failed."""
    db = tmp_path / "d.db"
    art = tmp_path / "a2"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)

    def boom(rid_: str, clinical: ClinicalOutput) -> CompetitorOutput:
        raise RuntimeError("competitor boom")

    monkeypatch.setattr("pharma_rd.pipeline.runner.competitor.run_competitor", boom)
    with pytest.raises(RuntimeError, match="competitor boom"):
        run_pipeline(conn, artifact_root=art, run_id=rid)

    with pytest.raises(ValueError, match="expected failed"):
        validate_stage_retry(conn, art, rid, "clinical")
