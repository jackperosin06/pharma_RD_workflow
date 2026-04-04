"""Clinical Data agent (stub)."""

from __future__ import annotations

from pharma_rd.pipeline.contracts import ClinicalOutput


def run_clinical(run_id: str) -> ClinicalOutput:
    """First stage: no upstream artifact; returns minimal valid structured output."""
    _ = run_id
    return ClinicalOutput()
