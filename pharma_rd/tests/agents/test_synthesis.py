"""Synthesis agent — FR14–FR17, FR27–FR28."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from pharma_rd.agents.synthesis import (
    RANKING_CRITERIA_VERSION,
    RANKING_CRITERIA_VERSION_GPT,
    run_synthesis,
)
from pharma_rd.config import get_settings
from pharma_rd.integrations.openai_synthesis import _build_user_payload
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerFeedbackThemeItem,
    ConsumerOutput,
    InternalResearchItem,
    PipelineDisclosureItem,
    PublicationItem,
    RegulatoryApprovalItem,
)


def _clinical(rid: str, *, gap: str | None = None) -> ClinicalOutput:
    return ClinicalOutput(
        run_id=rid,
        data_gaps=[gap] if gap else [],
    )


def _competitor(rid: str, *, gap: str | None = None) -> CompetitorOutput:
    return CompetitorOutput(
        run_id=rid,
        data_gaps=[gap] if gap else [],
    )


def _consumer(
    rid: str,
    *,
    gap: str | None = None,
    note: str | None = None,
) -> ConsumerOutput:
    return ConsumerOutput(
        run_id=rid,
        data_gaps=[gap] if gap else [],
        integration_notes=[note] if note else [],
    )


def test_run_synthesis_run_id_mismatch() -> None:
    with pytest.raises(ValueError, match="run_id mismatch"):
        run_synthesis(
            "rid-a",
            _clinical("rid-a"),
            _competitor("rid-b"),
            _consumer("rid-a"),
        )


def test_run_synthesis_aggregates_upstream_gaps_and_notes() -> None:
    out = run_synthesis(
        "rid-1",
        _clinical("rid-1", gap="c gap"),
        _competitor("rid-1", gap="p gap"),
        _consumer("rid-1", gap="u gap", note="FR12 hint"),
    )
    assert out.schema_version == 5
    assert out.run_id == "rid-1"
    assert out.ranking_criteria_version == RANKING_CRITERIA_VERSION
    assert out.ranked_opportunities == []
    assert out.upstream_clinical_schema_version == 3
    assert out.upstream_competitor_schema_version == 5
    assert out.upstream_consumer_schema_version == 5
    assert "[clinical] c gap" in out.aggregated_upstream_gaps
    assert "[competitor] p gap" in out.aggregated_upstream_gaps
    assert "[consumer] u gap" in out.aggregated_upstream_gaps
    assert any("FR12" in x for x in out.aggregated_upstream_gaps)
    assert out.signal_characterization == "quiet"
    assert len(out.scan_summary_lines) == 3
    assert "Clinical:" in out.scan_summary_lines[0]


def test_run_synthesis_empty_upstream_lists() -> None:
    out = run_synthesis(
        "rid-2",
        _clinical("rid-2"),
        _competitor("rid-2"),
        _consumer("rid-2"),
    )
    assert out.aggregated_upstream_gaps == []
    assert out.ranked_opportunities == []
    assert out.signal_characterization == "quiet"
    assert "Competitor:" in out.scan_summary_lines[1]


def test_run_synthesis_rich_upstream_cross_domain_ranking() -> None:
    rid = "rid-rich"
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=[
            PublicationItem(
                title="Trial Alpha",
                summary="Phase 2 signal for indication X.",
                reference="pmid:1",
            )
        ],
    )
    comp = CompetitorOutput(
        run_id=rid,
        approval_items=[
            RegulatoryApprovalItem(
                title="Approval Beta",
                summary="Label expansion in same class.",
                reference="fda:1",
                observed_at="2026-01-01T00:00:00Z",
            )
        ],
    )
    cons = ConsumerOutput(
        run_id=rid,
        feedback_themes=[
            ConsumerFeedbackThemeItem(
                theme="Itch relief",
                summary="Patients ask for longer duration.",
                source="forum",
            )
        ],
    )
    out = run_synthesis(rid, clin, comp, cons)
    assert out.schema_version == 5
    assert out.ranking_criteria_version == "cross_domain_v1"
    assert len(out.ranked_opportunities) == 1
    row = out.ranked_opportunities[0]
    assert row.rank == 1
    assert row.domain_coverage.clinical
    assert row.domain_coverage.competitor
    assert row.domain_coverage.consumer
    assert len(row.evidence_references) == 3
    domains = {e.domain for e in row.evidence_references}
    assert domains == {"clinical", "competitor", "consumer"}
    assert any("pmid:1" in e.reference for e in row.evidence_references)
    assert any("fda:1" in e.reference for e in row.evidence_references)
    assert any("forum" in e.reference for e in row.evidence_references)
    assert "Clinical:" in row.commercial_viability
    assert "Trial Alpha" in row.rationale_short
    assert "Approval Beta" in row.rationale_short
    assert "Itch relief" in row.rationale_short
    assert "Trial Alpha" in row.title
    assert out.signal_characterization == "net_new"
    assert "pubmed" in out.scan_summary_lines[0]
    assert "appr=1" in out.scan_summary_lines[1]


def test_run_synthesis_scan_summary_includes_ta_and_pipeline_scope() -> None:
    """FR28 substrings: configured TA and pipeline watch scope from upstream."""
    rid = "rid-fr28"
    clin = ClinicalOutput(
        run_id=rid,
        therapeutic_areas_configured=["Oncology"],
        publication_items=[
            PublicationItem(
                title="T",
                summary="s",
                reference="r",
                source="pubmed",
            )
        ],
    )
    comp = CompetitorOutput(
        run_id=rid,
        pipeline_disclosure_items=[
            PipelineDisclosureItem(
                title="Pipe",
                summary="ps",
                reference="ref",
                observed_at="2026-01-01T00:00:00Z",
                matched_scope="NSCLC",
            )
        ],
    )
    cons = ConsumerOutput(
        run_id=rid,
        practice_mode=False,
    )
    out = run_synthesis(rid, clin, comp, cons)
    scan = "\n".join(out.scan_summary_lines)
    assert "Oncology" in scan
    assert "NSCLC" in scan
    assert "practice_mode=False" in scan


def test_run_synthesis_partial_domains_index_alignment() -> None:
    """Second index has only clinical — rationale states competitor/consumer gaps."""
    rid = "rid-partial"
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=[
            PublicationItem(title="A1", summary="s1", reference="r1"),
            PublicationItem(title="A2", summary="s2", reference="r2"),
        ],
    )
    comp = CompetitorOutput(run_id=rid)
    cons = ConsumerOutput(run_id=rid)
    out = run_synthesis(rid, clin, comp, cons)
    assert out.signal_characterization == "mixed"
    assert len(out.ranked_opportunities) == 2
    # Both rows have clinical; rows sorted by domain coverage (3 > 1)
    top = out.ranked_opportunities[0]
    assert top.domain_coverage.clinical and not top.domain_coverage.competitor
    assert "No competitor signal" in top.rationale_short
    assert "No consumer signal" in top.rationale_short
    assert len(top.rationale_short) <= 281
    assert len(top.evidence_references) == 1
    assert top.evidence_references[0].domain == "clinical"
    assert "unknown" in top.commercial_viability.lower()


def test_run_synthesis_truncation_note_in_gaps() -> None:
    rid = "rid-trunc"
    pubs = [
        PublicationItem(title=f"T{i}", summary="s", reference="r") for i in range(6)
    ]
    clin = ClinicalOutput(run_id=rid, publication_items=pubs)
    out = run_synthesis(
        rid,
        clin,
        CompetitorOutput(run_id=rid),
        ConsumerOutput(run_id=rid),
    )
    assert any("truncated" in g.lower() for g in out.aggregated_upstream_gaps)
    assert any("[synthesis]" in g for g in out.aggregated_upstream_gaps)


def test_gpt_mode_without_api_key_falls_back_to_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_SYNTHESIS_MODE", "gpt")
    # Override any value from a local .env (delenv alone is not enough).
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "")
    get_settings.cache_clear()
    rid = "rid-no-key"
    out = run_synthesis(rid, _clinical(rid), _competitor(rid), _consumer(rid))
    assert out.ranking_criteria_version == "cross_domain_v1"
    assert any(
        "GPT synthesis skipped" in g and "OPENAI_API_KEY" in g
        for g in out.aggregated_upstream_gaps
    )


def test_gpt_synthesis_mocked_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_SYNTHESIS_MODE", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    rid = "rid-gpt"
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=[
            PublicationItem(
                title="Trial",
                summary="s",
                reference="pmid:9",
            )
        ],
    )
    comp = CompetitorOutput(run_id=rid)
    cons = ConsumerOutput(run_id=rid)
    payload = {
        "ranked_opportunities": [
            {
                "rank": 1,
                "title": "GPT row",
                "rationale_short": "Because clinical signal.",
                "domain_coverage": {
                    "clinical": True,
                    "competitor": False,
                    "consumer": False,
                },
                "evidence_references": [
                    {
                        "domain": "clinical",
                        "label": "Trial",
                        "reference": "pmid:9",
                    }
                ],
                "commercial_viability": "Early-stage; confirm externally.",
            }
        ],
        "signal_characterization": "mixed",
    }
    with patch(
        "pharma_rd.integrations.openai_synthesis.run_chat_json_completion",
        return_value=(json.dumps(payload), None),
    ):
        out = run_synthesis(rid, clin, comp, cons)
    assert out.ranking_criteria_version == RANKING_CRITERIA_VERSION_GPT
    assert len(out.ranked_opportunities) == 1
    assert out.ranked_opportunities[0].title == "GPT row"
    assert out.signal_characterization == "mixed"
    assert "Clinical:" in out.scan_summary_lines[0]


def test_build_user_payload_truncates_each_oversized_list() -> None:
    """Both publication and internal lists capped when both exceed 40 (code review)."""
    rid = "rid-cap"
    pubs = [
        PublicationItem(title=f"T{i}", summary="s", reference="r") for i in range(45)
    ]
    ir = [
        InternalResearchItem(title=f"I{i}", summary="s", reference="r")
        for i in range(45)
    ]
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=pubs,
        internal_research_items=ir,
    )
    raw = _build_user_payload(
        clin,
        CompetitorOutput(run_id=rid),
        ConsumerOutput(run_id=rid),
    )
    data = json.loads(raw)
    assert len(data["clinical"]["publication_items"]) == 40
    assert len(data["clinical"]["internal_research_items"]) == 40
    notes = data["clinical"]["_synthesis_prompt_notes"]
    assert len(notes) == 2
    assert "publication_items" in notes[0]
    assert "internal_research_items" in notes[1]


def test_gpt_synthesis_truncates_more_than_ten_ranked_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_SYNTHESIS_MODE", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    rid = "rid-12"
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=[
            PublicationItem(title="T", summary="s", reference="r"),
        ],
    )
    comp = CompetitorOutput(run_id=rid)
    cons = ConsumerOutput(run_id=rid)
    rows = []
    for i in range(12):
        rows.append(
            {
                "rank": i + 1,
                "title": f"Row{i}",
                "rationale_short": "x",
                "domain_coverage": {
                    "clinical": True,
                    "competitor": False,
                    "consumer": False,
                },
                "evidence_references": [
                    {
                        "domain": "clinical",
                        "label": "T",
                        "reference": "r",
                    }
                ],
                "commercial_viability": "c",
            }
        )
    payload = {"ranked_opportunities": rows, "signal_characterization": "mixed"}
    with patch(
        "pharma_rd.integrations.openai_synthesis.run_chat_json_completion",
        return_value=(json.dumps(payload), None),
    ):
        out = run_synthesis(rid, clin, comp, cons)
    assert len(out.ranked_opportunities) == 10
    assert any(
        "12" in g and "truncated" in g.lower()
        for g in out.aggregated_upstream_gaps
    )


def test_gpt_synthesis_retries_then_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_SYNTHESIS_MODE", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    rid = "rid-retry"
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=[
            PublicationItem(title="T", summary="s", reference="r"),
        ],
    )
    comp = CompetitorOutput(run_id=rid)
    cons = ConsumerOutput(run_id=rid)
    good = json.dumps(
        {
            "ranked_opportunities": [
                {
                    "rank": 1,
                    "title": "Ok",
                    "rationale_short": "x",
                    "domain_coverage": {
                        "clinical": True,
                        "competitor": False,
                        "consumer": False,
                    },
                    "evidence_references": [
                        {
                            "domain": "clinical",
                            "label": "T",
                            "reference": "r",
                        }
                    ],
                    "commercial_viability": "c",
                }
            ],
            "signal_characterization": "quiet",
        }
    )
    with patch(
        "pharma_rd.integrations.openai_synthesis.run_chat_json_completion",
        side_effect=[("{not json", None), (good, None)],
    ):
        out = run_synthesis(rid, clin, comp, cons)
    assert out.ranked_opportunities[0].title == "Ok"


def test_gpt_synthesis_fails_when_retry_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_SYNTHESIS_MODE", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    rid = "rid-bad"
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=[
            PublicationItem(title="T", summary="s", reference="r"),
        ],
    )
    comp = CompetitorOutput(run_id=rid)
    cons = ConsumerOutput(run_id=rid)
    bad = json.dumps({"ranked_opportunities": "not-a-list"})
    with patch(
        "pharma_rd.integrations.openai_synthesis.run_chat_json_completion",
        side_effect=[(bad, None), (bad, None)],
    ):
        with pytest.raises(ValueError, match="Synthesis GPT call failed"):
            run_synthesis(rid, clin, comp, cons)


def test_run_synthesis_skips_blank_publication_item() -> None:
    rid = "rid-blank"
    clin = ClinicalOutput(
        run_id=rid,
        publication_items=[
            PublicationItem(title="  ", summary="  ", reference="r"),
        ],
    )
    out = run_synthesis(
        rid,
        clin,
        CompetitorOutput(run_id=rid),
        ConsumerOutput(run_id=rid),
    )
    assert out.ranked_opportunities == []
    assert out.signal_characterization == "quiet"
    assert out.schema_version == 5
