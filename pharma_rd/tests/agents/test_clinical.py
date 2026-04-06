"""Clinical agent (FR6 / FR7 / NFR-I1)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from pharma_rd.agents.clinical import _SKIP_KEY_NOTE, run_clinical
from pharma_rd.config import get_settings
from pharma_rd.pipeline.contracts import (
    ClinicalGptAnalysis,
    ClinicalOutput,
    PublicationItem,
)

_FIXTURE_IR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "internal_research"
    / "sample.json"
)
_FIXTURE_CLINICAL = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "clinical"
    / "sample.json"
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_run_clinical_no_ta_configured() -> None:
    with patch.dict("os.environ", {"PHARMA_RD_THERAPEUTIC_AREAS": ""}, clear=False):
        out = run_clinical("run-a")
        assert isinstance(out, ClinicalOutput)
        assert out.schema_version == 3
        assert out.therapeutic_areas_configured == []
        assert out.publication_items == []
        assert any("PHARMA_RD_THERAPEUTIC_AREAS" in g for g in out.data_gaps)
        assert any(
            "internal research" in n.lower() and "not configured" in n.lower()
            for n in out.integration_notes
        )
        assert out.internal_research_items == []
        assert _SKIP_KEY_NOTE in out.integration_notes
        assert out.clinical_gpt_analysis is None


def test_run_clinical_loads_internal_research_fixture() -> None:
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_THERAPEUTIC_AREAS": "",
            "PHARMA_RD_INTERNAL_RESEARCH_PATH": str(_FIXTURE_IR),
        },
        clear=False,
    ):
        out = run_clinical("run-ir")
    assert len(out.internal_research_items) == 1
    assert "Practice-mode" in out.internal_research_items[0].title
    assert any("loaded" in n.lower() for n in out.integration_notes)


def test_run_clinical_fixture_skips_live_pubmed() -> None:
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_THERAPEUTIC_AREAS": "cardiovascular, pain management",
            "PHARMA_RD_CLINICAL_FIXTURE_PATH": str(_FIXTURE_CLINICAL),
        },
        clear=False,
    ):
        with patch(
            "pharma_rd.agents.clinical.fetch_publications_for_labels",
        ) as mock_pub:
            out = run_clinical("run-fixture")
            mock_pub.assert_not_called()
    assert len(out.publication_items) == 10
    assert out.therapeutic_areas_configured == ["cardiovascular", "pain management"]
    assert any("no live pubmed" in n.lower() for n in out.integration_notes)
    assert any("Semaglutide" in p.title for p in out.publication_items)
    assert _SKIP_KEY_NOTE in out.integration_notes


def test_run_clinical_fixture_without_ta_labels_adds_notes() -> None:
    with patch.dict(
        "os.environ",
        {"PHARMA_RD_CLINICAL_FIXTURE_PATH": str(_FIXTURE_CLINICAL)},
        clear=False,
    ):
        out = run_clinical("run-fix-no-ta")
    assert len(out.publication_items) == 10
    assert out.therapeutic_areas_configured == []
    assert any("demo data only" in n.lower() for n in out.integration_notes)


def test_run_clinical_with_mocked_pubmed() -> None:
    fake_items = [
        PublicationItem(
            title="T",
            summary="S",
            reference="https://pubmed.ncbi.nlm.nih.gov/123/",
            source="pubmed",
        )
    ]
    with patch.dict(
        "os.environ",
        {"PHARMA_RD_THERAPEUTIC_AREAS": "oncology"},
        clear=False,
    ):
        with patch(
            "pharma_rd.agents.clinical.fetch_publications_for_labels",
            return_value=(fake_items, ["note"], []),
        ):
            out = run_clinical("run-b")
    assert out.run_id == "run-b"
    assert len(out.publication_items) == 1
    assert out.publication_items[0].reference.endswith("/123/")
    assert "note" in out.integration_notes
    assert _SKIP_KEY_NOTE in out.integration_notes
    assert out.clinical_gpt_analysis is None


def test_run_clinical_gpt_enrichment_mocked() -> None:
    fake_items = [
        PublicationItem(
            title="Trial A",
            summary="Summary",
            reference="https://pubmed.ncbi.nlm.nih.gov/999/",
            source="pubmed",
        )
    ]
    gpt = ClinicalGptAnalysis(
        analyst_summary="Sig",
        ta_relevance_assessment="Relevant",
        priority_trials_attention=["Trial A"],
    )
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_THERAPEUTIC_AREAS": "oncology",
            "PHARMA_RD_OPENAI_API_KEY": "sk-test",
        },
        clear=False,
    ):
        with patch(
            "pharma_rd.agents.clinical.fetch_publications_for_labels",
            return_value=(fake_items, [], []),
        ):
            with patch(
                "pharma_rd.agents.clinical.call_clinical_gpt_analysis",
                return_value=(gpt, None),
            ):
                out = run_clinical("run-gpt")
    assert out.clinical_gpt_analysis == gpt
    assert out.clinical_gpt_analysis.analyst_summary == "Sig"
    assert _SKIP_KEY_NOTE not in out.integration_notes


def test_run_clinical_gpt_failure_degrades() -> None:
    fake_items = [
        PublicationItem(
            title="T",
            summary="S",
            reference="https://pubmed.ncbi.nlm.nih.gov/1/",
            source="pubmed",
        )
    ]
    with patch.dict(
        "os.environ",
        {
            "PHARMA_RD_THERAPEUTIC_AREAS": "oncology",
            "PHARMA_RD_OPENAI_API_KEY": "sk-test",
        },
        clear=False,
    ):
        with patch(
            "pharma_rd.agents.clinical.fetch_publications_for_labels",
            return_value=(fake_items, [], []),
        ):
            with patch(
                "pharma_rd.agents.clinical.call_clinical_gpt_analysis",
                return_value=(None, "RateLimitError: 429"),
            ):
                out = run_clinical("run-fail")
    assert out.clinical_gpt_analysis is None
    assert any("GPT clinical analysis failed" in n for n in out.integration_notes)
    assert any("RateLimitError" in g for g in out.data_gaps)


def test_run_clinical_no_signal_degrades_gracefully() -> None:
    """NFR-I1: empty PubMed result still yields valid structured output."""
    with patch.dict(
        "os.environ",
        {"PHARMA_RD_THERAPEUTIC_AREAS": "rarexyz123"},
        clear=False,
    ):
        with patch(
            "pharma_rd.agents.clinical.fetch_publications_for_labels",
            return_value=([], ["PubMed query: ...", "No PubMed IDs returned"], []),
        ):
            out = run_clinical("run-c")
    assert out.publication_items == []
    assert out.integration_notes
