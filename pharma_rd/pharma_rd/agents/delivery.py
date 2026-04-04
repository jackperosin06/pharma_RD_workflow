"""Delivery agent (stub)."""

from __future__ import annotations

from pharma_rd.pipeline.contracts import DeliveryOutput, SynthesisOutput


def run_delivery(run_id: str, synthesis: SynthesisOutput) -> DeliveryOutput:
    """Final stage: consumes synthesis output."""
    _ = run_id, synthesis
    return DeliveryOutput()
