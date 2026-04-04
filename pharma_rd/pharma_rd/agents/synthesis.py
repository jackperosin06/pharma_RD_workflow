"""Synthesis agent (stub)."""

from __future__ import annotations

from pharma_rd.pipeline.contracts import ConsumerOutput, SynthesisOutput


def run_synthesis(run_id: str, consumer: ConsumerOutput) -> SynthesisOutput:
    """Consumes consumer output."""
    _ = run_id, consumer
    return SynthesisOutput()
