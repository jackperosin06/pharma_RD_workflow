"""Ordered pipeline execution and stage contracts."""

from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerOutput,
    DeliveryOutput,
    SynthesisOutput,
)
from pharma_rd.pipeline.order import PIPELINE_ORDER

__all__ = [
    "PIPELINE_ORDER",
    "ClinicalOutput",
    "CompetitorOutput",
    "ConsumerOutput",
    "DeliveryOutput",
    "SynthesisOutput",
    "run_pipeline",
    "run_pipeline_resume_from",
]


def __getattr__(name: str):
    """Lazy-load runner to avoid import cycles when loading ``pipeline.contracts``."""
    if name == "run_pipeline":
        from pharma_rd.pipeline.runner import run_pipeline

        return run_pipeline
    if name == "run_pipeline_resume_from":
        from pharma_rd.pipeline.runner import run_pipeline_resume_from

        return run_pipeline_resume_from
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
