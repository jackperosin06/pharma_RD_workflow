"""Word (.docx) insight report builder."""

from __future__ import annotations

from pharma_rd.config import Settings
from pharma_rd.integrations.report_docx import build_insight_report_docx
from pharma_rd.pipeline.contracts import (
    DomainCoverage,
    RankedOpportunityItem,
    SynthesisOutput,
)


def test_build_insight_report_docx_produces_zip_payload() -> None:
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r1",
        signal_characterization="quiet",
        scan_summary_lines=["Clinical: pubs=0 tas=none"],
        ranked_opportunities=[
            RankedOpportunityItem(
                rank=1,
                title="Test opportunity",
                rationale_short="Because reasons.",
                domain_coverage=DomainCoverage(
                    clinical=True, competitor=False, consumer=False
                ),
                commercial_viability="Moderate.",
            )
        ],
    )
    raw = build_insight_report_docx("run-xyz", syn, Settings())
    assert raw[:2] == b"PK"
    assert b"word/document.xml" in raw
