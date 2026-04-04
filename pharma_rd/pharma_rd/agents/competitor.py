"""Competitor Intelligence agent (stub)."""

from __future__ import annotations

from pharma_rd.pipeline.contracts import ClinicalOutput, CompetitorOutput


def run_competitor(run_id: str, clinical: ClinicalOutput) -> CompetitorOutput:
    """Consumes clinical output; returns minimal valid structured output."""
    _ = run_id, clinical
    return CompetitorOutput()
