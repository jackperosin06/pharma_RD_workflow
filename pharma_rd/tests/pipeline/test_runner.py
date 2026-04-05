"""Integration tests for the ordered pipeline runner."""

from __future__ import annotations

import hashlib

import httpx
import pytest
from pharma_rd.http_client import ConnectorFailure, IntegrationErrorClass
from pharma_rd.persistence import connect, write_stage_artifact
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline import PIPELINE_ORDER, run_pipeline
from pharma_rd.pipeline.contracts import ClinicalOutput


def test_pipeline_runs_all_stages_in_order(tmp_path) -> None:
    db = tmp_path / "r.db"
    art = tmp_path / "artifacts"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)
    run_pipeline(conn, artifact_root=art, run_id=rid)

    row = conn.execute("SELECT status FROM runs WHERE run_id = ?", (rid,)).fetchone()
    assert row[0] == "completed"

    keys = [
        r[0]
        for r in conn.execute(
            "SELECT stage_key FROM stages WHERE run_id = ? ORDER BY id",
            (rid,),
        ).fetchall()
    ]
    assert tuple(keys) == PIPELINE_ORDER

    for sk in PIPELINE_ORDER:
        path = art / rid / sk / "output.json"
        assert path.is_file()
        raw = path.read_bytes()
        hx = hashlib.sha256(raw).hexdigest()
        meta = conn.execute(
            """
            SELECT sha256_hex FROM stage_artifacts
            WHERE run_id = ? AND stage_key = ?
            """,
            (rid, sk),
        ).fetchone()
        assert meta is not None
        assert meta[0] == hx


def test_pipeline_failure_marks_partial_failed_and_skips_downstream(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "f.db"
    art = tmp_path / "a"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)

    def boom(run_id: str, clinical: ClinicalOutput) -> None:
        _ = run_id, clinical
        raise RuntimeError("simulated competitor failure")

    monkeypatch.setattr("pharma_rd.pipeline.runner.competitor.run_competitor", boom)

    with pytest.raises(RuntimeError, match="simulated"):
        run_pipeline(conn, artifact_root=art, run_id=rid)

    run_status = conn.execute(
        "SELECT status FROM runs WHERE run_id = ?",
        (rid,),
    ).fetchone()[0]
    assert run_status == "partial_failed"

    comp = conn.execute(
        "SELECT status, error_summary FROM stages WHERE run_id = ? AND stage_key = ?",
        (rid, "competitor"),
    ).fetchone()
    assert comp[0] == "failed"
    assert comp[1] is not None
    assert "RuntimeError" in comp[1]
    assert "simulated competitor failure" in comp[1]

    n_consumer = conn.execute(
        "SELECT COUNT(*) FROM stages WHERE run_id = ? AND stage_key = ?",
        (rid, "consumer"),
    ).fetchone()[0]
    assert n_consumer == 0


def test_connector_failure_records_integration_class(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "c.db"
    art = tmp_path / "art"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)

    def boom(run_id: str, clinical: ClinicalOutput) -> None:
        _ = run_id, clinical
        raise ConnectorFailure(
            "upstream timed out",
            error_class=IntegrationErrorClass.TIMEOUT,
        )

    monkeypatch.setattr("pharma_rd.pipeline.runner.competitor.run_competitor", boom)

    with pytest.raises(ConnectorFailure):
        run_pipeline(conn, artifact_root=art, run_id=rid)

    comp = conn.execute(
        "SELECT status, error_summary FROM stages WHERE run_id = ? AND stage_key = ?",
        (rid, "competitor"),
    ).fetchone()
    assert comp[0] == "failed"
    assert comp[1] is not None
    assert "[timeout]" in comp[1]
    assert "upstream timed out" in comp[1]


def test_pipeline_with_connector_probe_uses_shared_client(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_CONNECTOR_PROBE_URL", "http://probe.test/stage")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    calls: list[tuple[str, str]] = []

    def fake_request(method: str, url: str, **kwargs: object) -> httpx.Response:
        calls.append((method, url))
        return httpx.Response(200)

    monkeypatch.setattr(
        "pharma_rd.agents.connector_probe.request_with_retries",
        fake_request,
    )

    db = tmp_path / "p.db"
    art = tmp_path / "a"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)
    run_pipeline(conn, artifact_root=art, run_id=rid)

    assert len(calls) == len(PIPELINE_ORDER)
    assert all(u == "http://probe.test/stage" for _, u in calls)


def test_write_stage_artifact_persists_metadata(tmp_path) -> None:
    db = tmp_path / "w.db"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn, run_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    m = ClinicalOutput(
        run_id=rid,
        therapeutic_areas_configured=[],
        data_gaps=["test artifact"],
    )
    rec = write_stage_artifact(
        conn,
        artifact_root=tmp_path / "ar",
        run_id=rid,
        stage_key="clinical",
        model=m,
    )
    assert rec.sha256_hex == hashlib.sha256(m.model_dump_json().encode()).hexdigest()
    row = conn.execute(
        "SELECT byte_size FROM stage_artifacts WHERE run_id = ?",
        (rid,),
    ).fetchone()
    assert row[0] == rec.byte_size
