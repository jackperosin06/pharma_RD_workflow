"""Structured JSON logging and correlation (story 1.4)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pharma_rd.persistence import connect
from pharma_rd.persistence.repository import RunRepository
from pharma_rd.pipeline import run_pipeline, run_pipeline_resume_from
from pharma_rd.pipeline.contracts import ClinicalOutput, CompetitorOutput
from pharma_rd.pipeline.resume_validation import validate_stage_retry


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
    started = next(r for r in rows if r.get("event") == "run_started")
    assert started.get("deployment_profile") == "practice"
    assert "run_completed" in events
    assert "stage_started" in events
    assert "stage_completed" in events
    assert "clinical_publications" in events
    assert "internal_research" in events
    assert "competitor_regulatory" in events
    assert "competitor_pipeline_disclosures" in events
    assert "competitor_patent_flags" in events
    assert "consumer_feedback" in events
    assert "consumer_pharmacy_sales" in events
    assert "consumer_unmet_need_demand" in events
    assert "synthesis_upstream_snapshot" in events
    assert "synthesis_ranking_complete" in events
    assert "delivery_report_written" in events
    assert "distribution_skipped" in events

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

    cf_ev = [r for r in rows if r.get("event") == "consumer_feedback"]
    assert len(cf_ev) == 1
    assert cf_ev[0]["stage"] == "consumer"
    assert "feedback_theme_count" in cf_ev[0]

    ps_ev = [r for r in rows if r.get("event") == "consumer_pharmacy_sales"]
    assert len(ps_ev) == 1
    assert ps_ev[0]["stage"] == "consumer"
    assert "sales_trend_count" in ps_ev[0]

    ud_ev = [r for r in rows if r.get("event") == "consumer_unmet_need_demand"]
    assert len(ud_ev) == 1
    assert ud_ev[0]["stage"] == "consumer"
    assert "unmet_need_demand_count" in ud_ev[0]

    syn_ev = [r for r in rows if r.get("event") == "synthesis_upstream_snapshot"]
    assert len(syn_ev) == 1
    assert syn_ev[0]["stage"] == "synthesis"
    assert "upstream_gap_count" in syn_ev[0]
    assert syn_ev[0].get("snapshot_ok") is True

    rank_ev = [r for r in rows if r.get("event") == "synthesis_ranking_complete"]
    assert len(rank_ev) == 1
    assert rank_ev[0]["stage"] == "synthesis"
    assert "ranked_count" in rank_ev[0]
    assert rank_ev[0].get("ranking_criteria_version") == "cross_domain_v1"
    assert "evidence_ref_count" in rank_ev[0]
    sig = rank_ev[0].get("signal_characterization")
    assert sig in ("quiet", "net_new", "mixed")
    assert rank_ev[0].get("scan_summary_line_count") == 3

    deliv_ev = [r for r in rows if r.get("event") == "delivery_report_written"]
    assert len(deliv_ev) == 1
    assert deliv_ev[0]["stage"] == "delivery"
    assert deliv_ev[0].get("report_relative_path")
    assert deliv_ev[0].get("report_byte_size", 0) > 0
    assert deliv_ev[0].get("report_html_relative_path")
    assert deliv_ev[0].get("report_html_byte_size", 0) > 0


def test_pipeline_resume_emits_deployment_profile_in_json(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "resume_log.db"
    art = tmp_path / "resume_art"
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

    validate_stage_retry(conn, art, rid, "competitor")

    run_pipeline_resume_from(
        conn,
        artifact_root=art,
        run_id=rid,
        start_stage_key="competitor",
    )

    rows = _parse_json_lines(capsys.readouterr().out)
    resume = next(r for r in rows if r.get("event") == "pipeline_resume")
    assert resume.get("deployment_profile") == "practice"
    assert resume.get("resumed_from_stage") == "competitor"


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
