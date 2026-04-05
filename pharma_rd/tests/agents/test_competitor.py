"""Competitor agent (FR8 / FR9 / NFR-I1)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pharma_rd.agents.competitor import run_competitor
from pharma_rd.config import get_settings
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    RegulatoryApprovalItem,
)

_CLINICAL = ClinicalOutput(run_id="upstream")
_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "competitor_regulatory"
    / "sample.json"
)


def test_run_competitor_no_watchlist() -> None:
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "",
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        out = run_competitor("run-x", _CLINICAL)
    assert isinstance(out, CompetitorOutput)
    assert out.approval_items == []
    assert out.disclosure_items == []
    assert out.pipeline_disclosure_items == []
    assert out.patent_filing_flags == []
    assert any("COMPETITOR_WATCHLIST" in g for g in out.data_gaps)
    assert any("PIPELINE_DISCLOSURE_SCOPES" in g for g in out.data_gaps)
    assert any("FR10 patent filing" in g for g in out.data_gaps)


def test_run_competitor_fixture_path() -> None:
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "AcmePharma",
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH": str(_FIXTURE),
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "Oncology",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        out = run_competitor("run-fix", _CLINICAL)
    assert len(out.approval_items) == 1
    assert len(out.disclosure_items) == 1
    assert len(out.pipeline_disclosure_items) == 1
    assert out.pipeline_disclosure_items[0].matched_scope == "Oncology"
    assert len(out.patent_filing_flags) == 1
    assert out.patent_filing_flags[0].matched_competitor == "AcmePharma"
    assert "Practice-mode" in out.approval_items[0].title
    assert "disclosure" in out.disclosure_items[0].title.lower()


def test_run_competitor_pipeline_scopes_no_match() -> None:
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "AcmePharma",
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH": str(_FIXTURE),
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "Cardiology",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        out = run_competitor("run-nomatch", _CLINICAL)
    assert out.pipeline_disclosure_items == []
    assert any("none found" in n.lower() for n in out.integration_notes)


def test_run_competitor_pipeline_scopes_without_fixture_path() -> None:
    fake_a = [
        RegulatoryApprovalItem(
            title="Mock drug",
            summary="Mock summary",
            reference="https://example.com/a",
            source_label="openfda",
            observed_at="2026-02-01T00:00:00Z",
        )
    ]
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "Pfizer",
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "Oncology",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        with patch(
            "pharma_rd.agents.competitor.fetch_openfda_approvals",
            return_value=(fake_a, ["note"], []),
        ):
            out = run_competitor("run-nopath", _CLINICAL)
    assert out.pipeline_disclosure_items == []
    assert out.patent_filing_flags == []
    notes = out.integration_notes
    assert any("PHARMA_RD_COMPETITOR_REGULATORY_PATH" in n for n in notes)


def test_run_competitor_pipeline_only_with_fixture() -> None:
    """FR9 can load pipeline rows without a competitor watchlist."""
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "",
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH": str(_FIXTURE),
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "Oncology",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        out = run_competitor("run-pipe", _CLINICAL)
    assert out.approval_items == []
    assert out.disclosure_items == []
    assert len(out.pipeline_disclosure_items) == 1
    assert out.patent_filing_flags == []
    assert any(
        "FR10" in n and "not evaluated" in n for n in out.integration_notes
    )
    assert any("COMPETITOR_WATCHLIST" in g for g in out.data_gaps)


def test_run_competitor_patent_tags_no_match() -> None:
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "OtherCo",
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH": str(_FIXTURE),
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        out = run_competitor("run-patnomatch", _CLINICAL)
    assert out.patent_filing_flags == []
    assert any("none found" in n.lower() for n in out.integration_notes)


def test_run_competitor_patent_row_without_competitor_tags_maps_to_first_label(
    tmp_path: Path,
) -> None:
    """Omitted ``competitor_tags`` applies the row to the first watchlist label (FR10 MVP)."""
    reg = {
        "patent_filing_flags": [
            {
                "title": "Patent row without competitor_tags",
                "summary": "Should match first configured watchlist label only.",
                "reference": "https://example.com/patent/omit-tags",
                "source_label": "fixture",
                "observed_at": "2026-01-25T15:00:00Z",
            }
        ]
    }
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(reg), encoding="utf-8")
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "AlphaCo,BetaCo",
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH": str(p),
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        out = run_competitor("run-pat-omit-tags", _CLINICAL)
    assert len(out.patent_filing_flags) == 1
    assert out.patent_filing_flags[0].matched_competitor == "AlphaCo"


def test_run_competitor_openfda_mocked() -> None:
    fake_a = [
        RegulatoryApprovalItem(
            title="Mock drug",
            summary="Mock summary",
            reference="https://example.com/a",
            source_label="openfda",
            observed_at="2026-02-01T00:00:00Z",
        )
    ]
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_COMPETITOR_WATCHLIST": "Pfizer",
            "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES": "",
        },
        clear=False,
    ):
        get_settings.cache_clear()
        with patch(
            "pharma_rd.agents.competitor.fetch_openfda_approvals",
            return_value=(fake_a, ["note"], []),
        ):
            out = run_competitor("run-of", _CLINICAL)
    assert len(out.approval_items) == 1
    assert out.approval_items[0].title == "Mock drug"
    assert out.disclosure_items == []
    assert out.pipeline_disclosure_items == []
    assert out.patent_filing_flags == []
    notes = out.integration_notes
    assert any("fixture" in n.lower() for n in notes) or any(
        "PHARMA_RD_COMPETITOR_REGULATORY_PATH" in n for n in notes
    )
    assert any("PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES empty" in n for n in notes)
