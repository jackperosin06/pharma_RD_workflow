"""Consumer Insight agent (stub)."""

from __future__ import annotations

from pharma_rd.pipeline.contracts import CompetitorOutput, ConsumerOutput


def run_consumer(run_id: str, competitor: CompetitorOutput) -> ConsumerOutput:
    """Consumes competitor output."""
    _ = run_id, competitor
    return ConsumerOutput()
