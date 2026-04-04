"""Delivery agent (stub)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.logging_setup import get_pipeline_logger, log_agent_stub
from pharma_rd.pipeline.contracts import DeliveryOutput, SynthesisOutput

_log = get_pipeline_logger("pharma_rd.agents.delivery")


def run_delivery(run_id: str, synthesis: SynthesisOutput) -> DeliveryOutput:
    """Final stage: consumes synthesis output."""
    _ = run_id, synthesis
    ensure_connector_probe("delivery")
    log_agent_stub(_log)
    return DeliveryOutput()
