"""Integration tests for the ordered pipeline runner."""

from __future__ import annotations

import hashlib

import pytest
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
        "SELECT status FROM stages WHERE run_id = ? AND stage_key = ?",
        (rid, "competitor"),
    ).fetchone()
    assert comp[0] == "failed"

    n_consumer = conn.execute(
        "SELECT COUNT(*) FROM stages WHERE run_id = ? AND stage_key = ?",
        (rid, "consumer"),
    ).fetchone()[0]
    assert n_consumer == 0


def test_write_stage_artifact_persists_metadata(tmp_path) -> None:
    db = tmp_path / "w.db"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn, run_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    m = ClinicalOutput(note="x")
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
