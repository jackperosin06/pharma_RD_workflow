"""Consumer Insight agent (stub)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.logging_setup import get_pipeline_logger, log_agent_stub
from pharma_rd.pipeline.contracts import CompetitorOutput, ConsumerOutput

_log = get_pipeline_logger("pharma_rd.agents.consumer")


def run_consumer(run_id: str, competitor: CompetitorOutput) -> ConsumerOutput:
    """Consumes competitor output."""
    _ = run_id, competitor
    ensure_connector_probe("consumer")
    log_agent_stub(_log)
    return ConsumerOutput()
