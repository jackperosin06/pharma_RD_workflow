"""Synthesis agent (stub)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.logging_setup import get_pipeline_logger, log_agent_stub
from pharma_rd.pipeline.contracts import ConsumerOutput, SynthesisOutput

_log = get_pipeline_logger("pharma_rd.agents.synthesis")


def run_synthesis(run_id: str, consumer: ConsumerOutput) -> SynthesisOutput:
    """Consumes consumer output."""
    _ = run_id, consumer
    ensure_connector_probe("synthesis")
    log_agent_stub(_log)
    return SynthesisOutput()
