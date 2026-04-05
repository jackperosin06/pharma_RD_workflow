"""Clinical agent (FR6 / FR7 / NFR-I1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pharma_rd.agents.clinical import run_clinical
from pharma_rd.pipeline.contracts import ClinicalOutput, PublicationItem

_FIXTURE_IR = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "internal_research"
    / "sample.json"
)


def test_run_clinical_no_ta_configured() -> None:
    with patch.dict("os.environ", {"PHARMA_RD_THERAPEUTIC_AREAS": ""}, clear=False):
        out = run_clinical("run-a")
        assert isinstance(out, ClinicalOutput)
        assert out.therapeutic_areas_configured == []
        assert out.publication_items == []
        assert any("PHARMA_RD_THERAPEUTIC_AREAS" in g for g in out.data_gaps)
        assert any(
            "internal research" in n.lower() and "not configured" in n.lower()
            for n in out.integration_notes
        )
        assert out.internal_research_items == []


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
