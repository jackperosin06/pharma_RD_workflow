"""Structured JSON logging and correlation (story 1.4)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pharma_rd.persistence import connect
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline import run_pipeline
from pharma_rd.pipeline.contracts import ClinicalOutput


def _parse_json_lines(stdout: str) -> list[dict[str, Any]]:
    lines = [ln for ln in stdout.strip().split("\n") if ln.strip()]
    return [json.loads(ln) for ln in lines]


def _assert_base_keys(row: dict[str, Any], *, run_id: str) -> None:
    assert row["run_id"] == run_id
    assert row["correlation_id"] == run_id
    assert row["level"] in ("INFO", "ERROR", "WARNING", "DEBUG")
    assert "message" in row
    assert "timestamp" in row and row["timestamp"].endswith("Z")


def test_pipeline_emits_json_lines_with_correlation(tmp_path, capsys) -> None:
    db = tmp_path / "l.db"
    art = tmp_path / "artifacts"
    conn = connect(db)
    repo = RunRepository()
    rid = repo.create_run(conn)
    run_pipeline(conn, artifact_root=art, run_id=rid)

    captured = capsys.readouterr()
    rows = _parse_json_lines(captured.out)
    assert len(rows) >= 1

    events = {r.get("event") for r in rows}
    assert "run_started" in events
    assert "run_completed" in events
    assert "stage_started" in events
    assert "stage_completed" in events
    assert "clinical_publications" in events
    assert "internal_research" in events
    assert "competitor_regulatory" in events
    assert "competitor_pipeline_disclosures" in events
    assert "competitor_patent_flags" in events
    assert "agent_stub" in events

    for row in rows:
        _assert_base_keys(row, run_id=rid)

    completed = next(r for r in rows if r.get("event") == "run_completed")
    assert completed.get("run_status") == "completed"
    assert completed.get("completed_stage_count") == 5

    clinical_ev = [r for r in rows if r.get("event") == "clinical_publications"]
    assert len(clinical_ev) == 1
    assert clinical_ev[0]["stage"] == "clinical"

    ir_ev = [r for r in rows if r.get("event") == "internal_research"]
    assert len(ir_ev) == 1
    assert ir_ev[0]["stage"] == "clinical"

    cr_ev = [r for r in rows if r.get("event") == "competitor_regulatory"]
    assert len(cr_ev) == 1
    assert cr_ev[0]["stage"] == "competitor"

    cp_ev = [r for r in rows if r.get("event") == "competitor_pipeline_disclosures"]
    assert len(cp_ev) == 1
    assert cp_ev[0]["stage"] == "competitor"

    pf_ev = [r for r in rows if r.get("event") == "competitor_patent_flags"]
    assert len(pf_ev) == 1
    assert pf_ev[0]["stage"] == "competitor"

    stub_rows = [r for r in rows if r.get("event") == "agent_stub"]
    assert len(stub_rows) == 3
    for sr in stub_rows:
        assert sr["stage"] in ("consumer", "synthesis", "delivery")
        assert sr["agent"] == sr["stage"]


def test_pipeline_failure_emits_stage_failed_and_run_failed(
    tmp_path,
    capsys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "e.db"
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

    rows = _parse_json_lines(capsys.readouterr().out)
    events = {r.get("event") for r in rows}
    assert "stage_failed" in events
    assert "run_failed" in events

    failed = next(r for r in rows if r.get("event") == "run_failed")
    assert failed["run_id"] == rid
    assert failed["correlation_id"] == rid
    assert failed.get("run_status") == "partial_failed"
    assert failed.get("completed_stage_count") == 1

    sf = next(r for r in rows if r.get("event") == "stage_failed")
    assert sf.get("stage") == "competitor"
    assert sf.get("error_type") == "RuntimeError"
