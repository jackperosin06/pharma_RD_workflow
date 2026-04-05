"""Competitor Intelligence agent — FR8–FR10 (regulatory, pipeline, patents)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.config import get_settings
from pharma_rd.integrations.regulatory_signals import (
    PatentFilingCandidate,
    PipelineDisclosureCandidate,
    fetch_openfda_approvals,
    filter_patent_filing_flags,
    filter_pipeline_disclosures,
    ingest_competitor_regulatory_fixture,
)
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    RegulatoryApprovalItem,
    RegulatoryDisclosureItem,
)

_log = get_pipeline_logger("pharma_rd.agents.competitor")


def run_competitor(run_id: str, clinical: ClinicalOutput) -> CompetitorOutput:
    """Surface FR8 approvals/disclosures, FR9 pipeline, FR10 patent flags."""
    _ = clinical
    ensure_connector_probe("competitor")
    settings = get_settings()
    labels = settings.competitor_labels()
    scope_labels = settings.pipeline_disclosure_scope_labels()
    obs_days = settings.competitor_observation_days

    if not labels and not scope_labels:
        _log.info(
            "competitor stage skipped outbound regulatory and pipeline queries",
            extra={
                "event": "competitor_regulatory",
                "outcome": "ok",
                "approval_count": 0,
                "disclosure_count": 0,
            },
        )
        _log.info(
            "competitor pipeline disclosures (FR9)",
            extra={
                "event": "competitor_pipeline_disclosures",
                "outcome": "skipped",
                "pipeline_disclosure_count": 0,
                "pipeline_scope_count": 0,
            },
        )
        _log.info(
            "competitor patent filing flags (FR10)",
            extra={
                "event": "competitor_patent_flags",
                "outcome": "skipped",
                "patent_flag_count": 0,
            },
        )
        return CompetitorOutput(
            run_id=run_id,
            data_gaps=[
                "No competitor watchlist configured. Set "
                "PHARMA_RD_COMPETITOR_WATCHLIST (comma-separated labels) to scope "
                "regulatory signals (FR24 / NFR-I1).",
                "FR9 pipeline disclosure watch scopes not configured. Set "
                "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES (comma-separated labels).",
                "FR10 patent filing flags require PHARMA_RD_COMPETITOR_WATCHLIST "
                "(comma-separated competitor labels).",
            ],
            integration_notes=[
                "Competitor stage completed without outbound OpenFDA, fixture load, "
                "or pipeline scope (empty watchlist and empty pipeline scopes)."
            ],
        )

    obs_note = (
        f"Observation window for this run: last {obs_days} calendar day(s) "
        "(UTC calendar-day semantics; item-level dates may be coarse in MVP)."
    )
    notes: list[str] = [obs_note]
    gaps: list[str] = []
    approvals: list[RegulatoryApprovalItem] = []
    disclosures: list[RegulatoryDisclosureItem] = []

    if not scope_labels:
        notes.append(
            "FR9 pipeline disclosure watch scopes not configured "
            "(PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES empty; NFR-I1)."
        )

    if not labels:
        gaps.append(
            "No competitor watchlist configured. Set "
            "PHARMA_RD_COMPETITOR_WATCHLIST (comma-separated labels) to scope "
            "regulatory signals (FR24 / NFR-I1)."
        )

    pipeline_candidates: list[PipelineDisclosureCandidate] = []
    patent_candidates: list[PatentFilingCandidate] = []
    if settings.competitor_regulatory_path is not None:
        fa, fd, pcand, pfcat, fn, fg = ingest_competitor_regulatory_fixture(settings)
        pipeline_candidates.extend(pcand)
        patent_candidates.extend(pfcat)
        if labels:
            approvals.extend(fa)
            disclosures.extend(fd)
        notes.extend(fn)
        gaps.extend(fg)
    elif labels:
        oa, on, og = fetch_openfda_approvals(labels, settings=settings)
        approvals.extend(oa)
        notes.extend(on)
        gaps.extend(og)
        notes.append(
            "Material regulatory disclosures in MVP: use "
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH with JSON fixtures for disclosure "
            "items; live OpenFDA drugsfda query surfaces approval-like records only."
        )

    pipeline_items, pipe_notes = filter_pipeline_disclosures(
        pipeline_candidates,
        scope_labels,
        fixture_path_configured=settings.competitor_regulatory_path is not None,
    )
    notes.extend(pipe_notes)

    patent_items, patent_notes = filter_patent_filing_flags(
        patent_candidates,
        labels,
        fixture_path_configured=settings.competitor_regulatory_path is not None,
    )
    notes.extend(patent_notes)

    _log.info(
        "competitor regulatory signals merged",
        extra={
            "event": "competitor_regulatory",
            "outcome": "ok",
            "approval_count": len(approvals),
            "disclosure_count": len(disclosures),
        },
    )
    _log.info(
        "competitor pipeline disclosures (FR9)",
        extra={
            "event": "competitor_pipeline_disclosures",
            "outcome": "ok",
            "pipeline_disclosure_count": len(pipeline_items),
            "pipeline_scope_count": len(scope_labels),
        },
    )
    _log.info(
        "competitor patent filing flags (FR10)",
        extra={
            "event": "competitor_patent_flags",
            "outcome": "ok",
            "patent_flag_count": len(patent_items),
        },
    )

    return CompetitorOutput(
        run_id=run_id,
        approval_items=approvals,
        disclosure_items=disclosures,
        pipeline_disclosure_items=pipeline_items,
        patent_filing_flags=patent_items,
        data_gaps=gaps,
        integration_notes=notes,
    )
