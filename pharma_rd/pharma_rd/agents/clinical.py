"""Clinical Data agent (stub)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.logging_setup import get_pipeline_logger, log_agent_stub
from pharma_rd.pipeline.contracts import ClinicalOutput

_log = get_pipeline_logger("pharma_rd.agents.clinical")


def run_clinical(run_id: str) -> ClinicalOutput:
    """First stage: no upstream artifact; returns minimal valid structured output."""
    _ = run_id
    ensure_connector_probe("clinical")
    log_agent_stub(_log)
    return ClinicalOutput()
