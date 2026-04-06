"""Executive framing for insight reports (humanized FR28 + gap partitioning)."""

from __future__ import annotations

from pharma_rd.integrations.report_executive_framing import (
    format_gap_line_for_report,
    humanize_scan_summary_line,
    partition_upstream_gaps,
    prepare_run_summary_for_report,
)
from pharma_rd.pipeline.contracts import SynthesisOutput


def test_partition_upstream_gaps_splits_integration() -> None:
    cov, op = partition_upstream_gaps(
        [
            "[clinical] configure TA",
            "[clinical:integration] PubMed query skipped",
            "[competitor] watchlist empty",
        ]
    )
    assert cov == ["[clinical] configure TA", "[competitor] watchlist empty"]
    assert op == ["[clinical:integration] PubMed query skipped"]


def test_humanize_scan_summary_clinical_competitor_consumer() -> None:
    assert "publication(s) in scope" in humanize_scan_summary_line(
        "Clinical: pubs=0 internal=0 tas=none"
    )
    assert "regulatory approvals surfaced" in humanize_scan_summary_line(
        "Competitor: appr=5 disc=0 pipe=0 patents=0"
    )
    assert "practice / demo data" in humanize_scan_summary_line(
        "Consumer: practice_mode=True feedback=1 sales=0 unmet=0"
    )


def test_format_gap_line_for_report() -> None:
    assert "Clinical —" in format_gap_line_for_report("[clinical] No TA configured.")
    assert "Technical (clinical):" in format_gap_line_for_report(
        "[clinical:integration] Outbound query empty."
    )


def test_prepare_run_summary_for_report_counts() -> None:
    gaps = [f"[clinical] gap {i}" for i in range(10)]
    gaps.append("[clinical:integration] note")
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r",
        signal_characterization="mixed",
        scan_summary_lines=["Clinical: pubs=0 internal=0 tas=none"],
        aggregated_upstream_gaps=gaps,
    )
    parts = prepare_run_summary_for_report(syn)
    assert len(parts.coverage_gap_lines) == 8
    assert parts.coverage_remaining == 2
    assert len(parts.operator_gap_lines) == 1
    assert parts.operator_remaining == 0
