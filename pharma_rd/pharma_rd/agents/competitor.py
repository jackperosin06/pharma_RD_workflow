"""Competitor Intelligence agent (stub)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.logging_setup import get_pipeline_logger, log_agent_stub
from pharma_rd.pipeline.contracts import ClinicalOutput, CompetitorOutput

_log = get_pipeline_logger("pharma_rd.agents.competitor")


def run_competitor(run_id: str, clinical: ClinicalOutput) -> CompetitorOutput:
    """Consumes clinical output; returns minimal valid structured output."""
    _ = run_id, clinical
    ensure_connector_probe("competitor")
    log_agent_stub(_log)
    return CompetitorOutput()
