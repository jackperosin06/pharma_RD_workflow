"""Clinical Data agent — PubMed + internal research (Epic 3 / FR6–FR7)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.config import Settings, get_settings
from pharma_rd.integrations.internal_research import ingest_internal_research
from pharma_rd.integrations.pubmed import fetch_publications_for_labels
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.pipeline.contracts import ClinicalOutput

_log = get_pipeline_logger("pharma_rd.agents.clinical")


def _merge_internal_research(
    base: ClinicalOutput,
    settings: Settings,
) -> ClinicalOutput:
    ir_items, ir_notes, ir_gaps = ingest_internal_research(settings)
    return base.model_copy(
        update={
            "internal_research_items": ir_items,
            "integration_notes": list(base.integration_notes) + ir_notes,
            "data_gaps": list(base.data_gaps) + ir_gaps,
        }
    )


def run_clinical(run_id: str) -> ClinicalOutput:
    """PubMed discovery for configured TAs; merge internal research JSON when set."""
    ensure_connector_probe("clinical")
    settings = get_settings()
    labels = settings.therapeutic_area_labels()

    if not labels:
        _log.info(
            "clinical stage completed without PubMed query (no TA scope)",
            extra={
                "event": "clinical_publications",
                "outcome": "ok",
                "publication_count": 0,
            },
        )
        base = ClinicalOutput(
            run_id=run_id,
            therapeutic_areas_configured=[],
            data_gaps=[
                "No therapeutic areas configured. Set PHARMA_RD_THERAPEUTIC_AREAS "
                "(comma-separated labels) to scope PubMed discovery (FR23 / NFR-I1)."
            ],
            integration_notes=[
                "Clinical stage completed without outbound PubMed query "
                "(empty TA scope)."
            ],
        )
    else:
        items, notes, gaps = fetch_publications_for_labels(labels, settings=settings)

        _log.info(
            "clinical publications retrieved",
            extra={
                "event": "clinical_publications",
                "outcome": "ok",
                "publication_count": len(items),
            },
        )

        base = ClinicalOutput(
            run_id=run_id,
            therapeutic_areas_configured=labels,
            publication_items=items,
            data_gaps=gaps,
            integration_notes=notes,
        )

    out = _merge_internal_research(base, settings)
    _log.info(
        "internal research merged",
        extra={
            "event": "internal_research",
            "outcome": "ok",
            "internal_research_count": len(out.internal_research_items),
        },
    )
    return out
