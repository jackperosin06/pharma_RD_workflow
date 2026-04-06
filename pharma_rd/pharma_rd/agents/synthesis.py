"""Synthesis agent — FR14–FR17 + FR27–FR28 (Epic 6)."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.config import get_settings
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerFeedbackThemeItem,
    ConsumerOutput,
    DomainCoverage,
    EvidenceReferenceItem,
    InternalResearchItem,
    PatentFilingFlagItem,
    PharmacySalesTrendItem,
    PipelineDisclosureItem,
    PublicationItem,
    RankedOpportunityItem,
    RegulatoryApprovalItem,
    RegulatoryDisclosureItem,
    SignalCharacterization,
    SynthesisOutput,
    UnmetNeedDemandSignalItem,
)

_log = get_pipeline_logger("pharma_rd.agents.synthesis")

RANKING_CRITERIA_VERSION = "cross_domain_v1"
RANKING_CRITERIA_VERSION_GPT = "gpt_strategy_v1"
_MAX_PER_DOMAIN = 5
_MAX_RANKED_ROWS = 10
_RATIONALE_MAX_LEN = 280
_COMMERCIAL_VIABILITY_MAX_LEN = 400
# Evidence reference strings (URLs, PMID lists); separate from label cap (code review).
_REFERENCE_MAX_LEN = 500

# Row tuple: title, summary, evidence for that slice (same index across domains).
ClinicalRow = tuple[str, str, EvidenceReferenceItem]
CompetitorRow = tuple[str, str, EvidenceReferenceItem]
ConsumerRow = tuple[str, str, EvidenceReferenceItem]


def _clip(text: str, max_len: int) -> str:
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _pair_usable(title: str, summary: str) -> bool:
    """Skip rows with no usable text for ranking (code review patch)."""
    return bool(title.strip() or summary.strip())


def _verification_ref(*parts: str, fallback: str = "") -> str:
    """Prefer first non-empty upstream verification string (FR16); else ``fallback``."""
    for p in parts:
        s = (p or "").strip()
        if s:
            return s
    return (fallback or "").strip()


def _aggregate_upstream_lines(
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> list[str]:
    """Merge upstream data_gaps and integration_notes with stage labels (NFR-I1)."""
    lines: list[str] = []
    for label, model in (
        ("clinical", clinical),
        ("competitor", competitor),
        ("consumer", consumer),
    ):
        for g in model.data_gaps:
            lines.append(f"[{label}] {g}")
        for n in model.integration_notes:
            lines.append(f"[{label}:integration] {n}")
    return lines


def _evidence_publication(p: PublicationItem) -> EvidenceReferenceItem:
    label = _clip(p.title, 120)
    fb = p.title.strip() or p.summary.strip()
    ref = _verification_ref(
        p.reference, p.source, p.title, p.summary, fallback=fb
    )
    return EvidenceReferenceItem(
        domain="clinical",
        label=label,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _evidence_internal(p: InternalResearchItem) -> EvidenceReferenceItem:
    label = _clip(p.title, 120)
    fb = p.title.strip() or p.summary.strip()
    ref = _verification_ref(
        p.reference, p.source_label, p.title, p.summary, fallback=fb
    )
    return EvidenceReferenceItem(
        domain="clinical",
        label=label,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _collect_clinical(
    clinical: ClinicalOutput,
) -> tuple[list[ClinicalRow], str | None]:
    raw_pairs: list[tuple[str, str]] = []
    for p in clinical.publication_items:
        raw_pairs.append((p.title, p.summary))
    for p in clinical.internal_research_items:
        raw_pairs.append((p.title, p.summary))
    n_raw = len(raw_pairs)

    rows: list[ClinicalRow] = []
    for p in clinical.publication_items:
        if not _pair_usable(p.title, p.summary):
            continue
        ev = _evidence_publication(p)
        rows.append((p.title, p.summary, ev))
    for p in clinical.internal_research_items:
        if not _pair_usable(p.title, p.summary):
            continue
        ev = _evidence_internal(p)
        rows.append((p.title, p.summary, ev))

    if len(rows) > _MAX_PER_DOMAIN:
        return rows[:_MAX_PER_DOMAIN], (
            f"[synthesis] Clinical inputs truncated for ranking: "
            f"{_MAX_PER_DOMAIN} of {len(rows)} usable items "
            f"(from {n_raw} raw rows)."
        )
    return rows, None


def _evidence_approval(p: RegulatoryApprovalItem) -> EvidenceReferenceItem:
    label = _clip(p.title, 120)
    fb = p.title.strip() or p.summary.strip()
    ref = _verification_ref(
        p.reference, p.source_label, p.title, p.summary, fallback=fb
    )
    return EvidenceReferenceItem(
        domain="competitor",
        label=label,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _evidence_disclosure(p: RegulatoryDisclosureItem) -> EvidenceReferenceItem:
    label = _clip(p.title, 120)
    fb = p.title.strip() or p.summary.strip()
    ref = _verification_ref(
        p.reference, p.source_label, p.title, p.summary, fallback=fb
    )
    return EvidenceReferenceItem(
        domain="competitor",
        label=label,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _evidence_pipeline(p: PipelineDisclosureItem) -> EvidenceReferenceItem:
    label = _clip(p.title, 120)
    fb = (
        p.title.strip()
        or p.summary.strip()
        or p.matched_scope.strip()
    )
    ref = _verification_ref(
        p.reference,
        p.source_label,
        p.matched_scope,
        p.title,
        p.summary,
        fallback=fb,
    )
    return EvidenceReferenceItem(
        domain="competitor",
        label=label,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _evidence_patent(p: PatentFilingFlagItem) -> EvidenceReferenceItem:
    label = _clip(p.title, 120)
    fb = (
        p.title.strip()
        or p.summary.strip()
        or p.matched_competitor.strip()
    )
    ref = _verification_ref(
        p.reference,
        p.source_label,
        p.matched_competitor,
        p.title,
        p.summary,
        fallback=fb,
    )
    return EvidenceReferenceItem(
        domain="competitor",
        label=label,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _collect_competitor(
    competitor: CompetitorOutput,
) -> tuple[list[CompetitorRow], str | None]:
    raw_pairs: list[tuple[str, str]] = []
    for p in competitor.approval_items:
        raw_pairs.append((p.title, p.summary))
    for p in competitor.disclosure_items:
        raw_pairs.append((p.title, p.summary))
    for p in competitor.pipeline_disclosure_items:
        raw_pairs.append((p.title, p.summary))
    for p in competitor.patent_filing_flags:
        raw_pairs.append((p.title, p.summary))
    n_raw = len(raw_pairs)

    rows: list[CompetitorRow] = []
    for p in competitor.approval_items:
        if not _pair_usable(p.title, p.summary):
            continue
        rows.append((p.title, p.summary, _evidence_approval(p)))
    for p in competitor.disclosure_items:
        if not _pair_usable(p.title, p.summary):
            continue
        rows.append((p.title, p.summary, _evidence_disclosure(p)))
    for p in competitor.pipeline_disclosure_items:
        if not _pair_usable(p.title, p.summary):
            continue
        rows.append((p.title, p.summary, _evidence_pipeline(p)))
    for p in competitor.patent_filing_flags:
        if not _pair_usable(p.title, p.summary):
            continue
        rows.append((p.title, p.summary, _evidence_patent(p)))

    if len(rows) > _MAX_PER_DOMAIN:
        return rows[:_MAX_PER_DOMAIN], (
            f"[synthesis] Competitor inputs truncated for ranking: "
            f"{_MAX_PER_DOMAIN} of {len(rows)} usable items "
            f"(from {n_raw} raw rows)."
        )
    return rows, None


def _evidence_feedback(p: ConsumerFeedbackThemeItem) -> EvidenceReferenceItem:
    lab = _clip(p.theme, 120)
    fb = p.theme.strip() or p.summary.strip()
    ref = _verification_ref(p.source, p.theme, p.summary, fallback=fb)
    return EvidenceReferenceItem(
        domain="consumer",
        label=lab,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _evidence_sales(p: PharmacySalesTrendItem) -> EvidenceReferenceItem:
    disp = f"{p.scope} sales" if p.scope else "Pharmacy sales"
    lab = _clip(disp, 120)
    fb = p.source.strip() or p.scope.strip() or p.summary.strip() or disp
    ref = _verification_ref(p.source, p.scope, p.summary, fallback=fb)
    return EvidenceReferenceItem(
        domain="consumer",
        label=lab,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _evidence_unmet(p: UnmetNeedDemandSignalItem) -> EvidenceReferenceItem:
    lab = _clip(p.signal, 120)
    fb = p.signal.strip() or p.summary.strip()
    ref = _verification_ref(p.source, p.signal, p.summary, fallback=fb)
    return EvidenceReferenceItem(
        domain="consumer",
        label=lab,
        reference=_clip(ref, _REFERENCE_MAX_LEN),
    )


def _collect_consumer(
    consumer: ConsumerOutput,
) -> tuple[list[ConsumerRow], str | None]:
    raw_pairs: list[tuple[str, str]] = []
    for p in consumer.feedback_themes:
        raw_pairs.append((p.theme, p.summary))
    for p in consumer.pharmacy_sales_trends:
        label = f"{p.scope} sales" if p.scope else "Pharmacy sales"
        raw_pairs.append((label, p.summary))
    for p in consumer.unmet_need_demand_signals:
        raw_pairs.append((p.signal, p.summary))
    n_raw = len(raw_pairs)

    rows: list[ConsumerRow] = []
    for p in consumer.feedback_themes:
        if not _pair_usable(p.theme, p.summary):
            continue
        rows.append((p.theme, p.summary, _evidence_feedback(p)))
    for p in consumer.pharmacy_sales_trends:
        if not _pair_usable(
            f"{p.scope} sales" if p.scope else "Pharmacy sales", p.summary
        ):
            continue
        label = f"{p.scope} sales" if p.scope else "Pharmacy sales"
        rows.append((label, p.summary, _evidence_sales(p)))
    for p in consumer.unmet_need_demand_signals:
        if not _pair_usable(p.signal, p.summary):
            continue
        rows.append((p.signal, p.summary, _evidence_unmet(p)))

    if len(rows) > _MAX_PER_DOMAIN:
        return rows[:_MAX_PER_DOMAIN], (
            f"[synthesis] Consumer inputs truncated for ranking: "
            f"{_MAX_PER_DOMAIN} of {len(rows)} usable items "
            f"(from {n_raw} raw rows)."
        )
    return rows, None


def _ts(
    row: ClinicalRow | CompetitorRow | ConsumerRow | None,
) -> tuple[str, str] | None:
    if row is None:
        return None
    return row[0], row[1]


def _compose_title(
    ci: ClinicalRow | CompetitorRow | ConsumerRow | None,
    pi: ClinicalRow | CompetitorRow | ConsumerRow | None,
    ui: ClinicalRow | CompetitorRow | ConsumerRow | None,
) -> str:
    parts: list[str] = []
    tsi = _ts(ci)
    if tsi:
        parts.append(f"Clinical: {_clip(tsi[0], 28)}")
    else:
        parts.append("Clinical: (no item)")
    tsp = _ts(pi)
    if tsp:
        parts.append(f"Competitor: {_clip(tsp[0], 28)}")
    else:
        parts.append("Competitor: (no item)")
    tsu = _ts(ui)
    if tsu:
        parts.append(f"Consumer: {_clip(tsu[0], 28)}")
    else:
        parts.append("Consumer: (no item)")
    return " · ".join(parts)


def _compose_rationale(
    ci: ClinicalRow | CompetitorRow | ConsumerRow | None,
    pi: ClinicalRow | CompetitorRow | ConsumerRow | None,
    ui: ClinicalRow | CompetitorRow | ConsumerRow | None,
) -> str:
    """One or two sentences; states domain gaps without inventing ties."""
    segs: list[str] = []
    tsi = _ts(ci)
    if tsi:
        segs.append(
            f"Clinical “{_clip(tsi[0], 36)}”: {_clip(tsi[1], 72)}"
        )
    else:
        segs.append("No clinical signal at this slice index.")
    tsp = _ts(pi)
    if tsp:
        segs.append(
            f"Competitor “{_clip(tsp[0], 36)}”: {_clip(tsp[1], 72)}"
        )
    else:
        segs.append("No competitor signal at this slice index.")
    tsu = _ts(ui)
    if tsu:
        segs.append(
            f"Consumer “{_clip(tsu[0], 36)}”: {_clip(tsu[1], 72)}"
        )
    else:
        segs.append("No consumer signal at this slice index.")
    joined = " ".join(segs)
    return _clip(joined, _RATIONALE_MAX_LEN)


def _compose_commercial_viability(
    cov: DomainCoverage,
) -> str:
    """Deterministic qualitative framing (FR17); no LLM."""
    segs: list[str] = []
    if cov.clinical:
        segs.append(
            "Clinical: cited evidence supports development relevance for this slice."
        )
    else:
        segs.append("Clinical: not available at this slice index.")
    if cov.competitor:
        segs.append(
            "Competitive/regulatory: review timing and differentiation (cited refs)."
        )
    else:
        segs.append("Competitive/regulatory: unknown at this slice index.")
    if cov.consumer:
        segs.append(
            "Market/demand: consumer signals present; validate externally before GTM."
        )
    else:
        segs.append("Market/demand: unknown at this slice index.")
    return _clip(" ".join(segs), _COMMERCIAL_VIABILITY_MAX_LEN)


def _collect_all_domains(
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> tuple[
    list[ClinicalRow],
    list[CompetitorRow],
    list[ConsumerRow],
    list[str],
]:
    """Collect usable per-domain rows once; append synthesis truncation notes."""
    c, cn = _collect_clinical(clinical)
    p, pn = _collect_competitor(competitor)
    u, un = _collect_consumer(consumer)
    notes = [x for x in (cn, pn, un) if x]
    return c, p, u, notes


def _build_ranked_from_lists(
    c: list[ClinicalRow],
    p: list[CompetitorRow],
    u: list[ConsumerRow],
) -> list[RankedOpportunityItem]:
    """Index-aligned usable slices per domain; sorted by coverage."""
    if not c and not p and not u:
        return []

    span = max(len(c), len(p), len(u))
    n = min(_MAX_RANKED_ROWS, span)
    raw: list[
        tuple[int, int, str, str, DomainCoverage, list[EvidenceReferenceItem], str]
    ] = []
    for i in range(n):
        ci = c[i] if i < len(c) else None
        pi = p[i] if i < len(p) else None
        ui = u[i] if i < len(u) else None
        cov = DomainCoverage(
            clinical=ci is not None,
            competitor=pi is not None,
            consumer=ui is not None,
        )
        dc = cov.clinical + cov.competitor + cov.consumer
        title = _compose_title(ci, pi, ui)
        rationale = _compose_rationale(ci, pi, ui)
        evidence: list[EvidenceReferenceItem] = []
        if ci:
            evidence.append(ci[2])
        if pi:
            evidence.append(pi[2])
        if ui:
            evidence.append(ui[2])
        cv = _compose_commercial_viability(cov)
        raw.append((-dc, i, title, rationale, cov, evidence, cv))

    raw.sort(key=lambda t: (t[0], t[1]))
    ranked: list[RankedOpportunityItem] = []
    for pos, (_, _, title, rationale, cov, evidence, cv) in enumerate(raw, start=1):
        ranked.append(
            RankedOpportunityItem(
                rank=pos,
                title=title,
                rationale_short=rationale,
                domain_coverage=cov,
                evidence_references=evidence,
                commercial_viability=cv,
            )
        )
    return ranked


def _domain_coverage_count(cov: DomainCoverage) -> int:
    return int(cov.clinical) + int(cov.competitor) + int(cov.consumer)


def _characterize_signal(
    ranked: list[RankedOpportunityItem],
) -> SignalCharacterization:
    """FR27 deterministic characterization (no LLM).

    - **quiet:** no ranked rows (nothing cross-domain to prioritize this run).
    - **net_new:** at least one row spans **≥2** monitoring domains (material tie-in).
    - **mixed:** ranked rows exist but each row is **single-domain** only.
    """
    if not ranked:
        return "quiet"
    if any(_domain_coverage_count(r.domain_coverage) >= 2 for r in ranked):
        return "net_new"
    return "mixed"


def _uniq_join(values: list[str], *, limit: int = 6) -> str:
    ordered = sorted({v.strip() for v in values if v.strip()})
    return ",".join(ordered[:limit])


def _build_scan_summary(
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> list[str]:
    """FR28: scopes/sources actually present in upstream structured outputs."""
    tas = ", ".join(clinical.therapeutic_areas_configured) or "none"
    pub_sources = _uniq_join([p.source for p in clinical.publication_items])
    int_labels = _uniq_join([p.source_label for p in clinical.internal_research_items])
    c_line = (
        f"Clinical: pubs={len(clinical.publication_items)} "
        f"internal={len(clinical.internal_research_items)} tas={tas}"
    )
    if pub_sources:
        c_line += f" pub_src={pub_sources}"
    if int_labels:
        c_line += f" internal_lbl={int_labels}"
    lines: list[str] = [_clip(c_line, 88)]

    pipe_scopes = _uniq_join(
        [p.matched_scope for p in competitor.pipeline_disclosure_items]
    )
    pat_comp = _uniq_join(
        [p.matched_competitor for p in competitor.patent_filing_flags]
    )
    p_line = (
        f"Competitor: appr={len(competitor.approval_items)} "
        f"disc={len(competitor.disclosure_items)} "
        f"pipe={len(competitor.pipeline_disclosure_items)} "
        f"patents={len(competitor.patent_filing_flags)}"
    )
    if pipe_scopes:
        p_line += f" pipe_scopes={pipe_scopes}"
    if pat_comp:
        p_line += f" patent_comp={pat_comp}"
    lines.append(_clip(p_line, 88))

    sales_scopes = _uniq_join(
        [p.scope for p in consumer.pharmacy_sales_trends if p.scope]
    )
    u_line = (
        f"Consumer: practice_mode={consumer.practice_mode} "
        f"feedback={len(consumer.feedback_themes)} "
        f"sales={len(consumer.pharmacy_sales_trends)} "
        f"unmet={len(consumer.unmet_need_demand_signals)}"
    )
    if sales_scopes:
        u_line += f" sales_scopes={sales_scopes}"
    lines.append(_clip(u_line, 88))
    return lines


def _run_synthesis_deterministic(
    run_id: str,
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> SynthesisOutput:
    """Legacy cross-domain ranking without LLM (synthesis_mode=deterministic)."""
    gaps = _aggregate_upstream_lines(clinical, competitor, consumer)
    c, p, u, synth_notes = _collect_all_domains(clinical, competitor, consumer)
    gaps.extend(synth_notes)
    ranked = _build_ranked_from_lists(c, p, u)
    evidence_ref_count = sum(len(r.evidence_references) for r in ranked)
    sig = _characterize_signal(ranked)
    scan_lines = _build_scan_summary(clinical, competitor, consumer)
    _log.info(
        "synthesis upstream snapshot loaded",
        extra={
            "event": "synthesis_upstream_snapshot",
            "outcome": "ok",
            "upstream_gap_count": len(gaps),
            "snapshot_ok": True,
        },
    )
    _log.info(
        "synthesis ranking complete",
        extra={
            "event": "synthesis_ranking_complete",
            "outcome": "ok",
            "ranked_count": len(ranked),
            "ranking_criteria_version": RANKING_CRITERIA_VERSION,
            "evidence_ref_count": evidence_ref_count,
            "signal_characterization": sig,
            "scan_summary_line_count": len(scan_lines),
        },
    )
    return SynthesisOutput(
        schema_version=5,
        run_id=run_id,
        upstream_clinical_schema_version=clinical.schema_version,
        upstream_competitor_schema_version=competitor.schema_version,
        upstream_consumer_schema_version=consumer.schema_version,
        aggregated_upstream_gaps=gaps,
        ranking_criteria_version=RANKING_CRITERIA_VERSION,
        ranked_opportunities=ranked,
        signal_characterization=sig,
        scan_summary_lines=scan_lines,
    )


def _run_synthesis_gpt(
    run_id: str,
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> SynthesisOutput:
    """OpenAI JSON synthesis (PHARMA_RD_SYNTHESIS_MODE=gpt and API key set)."""
    from pharma_rd.integrations.openai_synthesis import call_synthesis_gpt

    settings = get_settings()
    partial, err = call_synthesis_gpt(settings, clinical, competitor, consumer)
    if err or partial is None:
        raise ValueError(
            "Synthesis GPT call failed: "
            f"{err or 'unknown_error'}. "
            "Check PHARMA_RD_OPENAI_API_KEY and "
            "PHARMA_RD_OPENAI_SYNTHESIS_TIMEOUT_SECONDS, and logs; or set "
            "PHARMA_RD_SYNTHESIS_MODE=deterministic for offline runs."
        )
    _, _, _, synth_notes = _collect_all_domains(clinical, competitor, consumer)
    gaps = _aggregate_upstream_lines(clinical, competitor, consumer)
    gaps.extend(synth_notes)
    gaps.extend(partial.operator_notes)
    scan_lines = _build_scan_summary(clinical, competitor, consumer)
    evidence_ref_count = sum(
        len(r.evidence_references) for r in partial.ranked_opportunities
    )
    _log.info(
        "synthesis upstream snapshot loaded",
        extra={
            "event": "synthesis_upstream_snapshot",
            "outcome": "ok",
            "upstream_gap_count": len(gaps),
            "snapshot_ok": True,
        },
    )
    _log.info(
        "synthesis ranking complete",
        extra={
            "event": "synthesis_ranking_complete",
            "outcome": "ok",
            "ranked_count": len(partial.ranked_opportunities),
            "ranking_criteria_version": RANKING_CRITERIA_VERSION_GPT,
            "evidence_ref_count": evidence_ref_count,
            "signal_characterization": partial.signal_characterization,
            "scan_summary_line_count": len(scan_lines),
        },
    )
    return SynthesisOutput(
        schema_version=5,
        run_id=run_id,
        upstream_clinical_schema_version=clinical.schema_version,
        upstream_competitor_schema_version=competitor.schema_version,
        upstream_consumer_schema_version=consumer.schema_version,
        aggregated_upstream_gaps=gaps,
        ranking_criteria_version=RANKING_CRITERIA_VERSION_GPT,
        ranked_opportunities=partial.ranked_opportunities,
        signal_characterization=partial.signal_characterization,
        scan_summary_lines=scan_lines,
    )


def run_synthesis(
    run_id: str,
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> SynthesisOutput:
    """FR14 snapshot, FR15–FR17 ranked rows, FR27–FR28 signal + scan summary."""
    ids = (clinical.run_id, competitor.run_id, consumer.run_id)
    if not all(r == run_id for r in ids):
        raise ValueError(
            "run_id mismatch across upstream outputs: "
            f"expected {run_id!r}, got "
            f"clinical={clinical.run_id!r}, competitor={competitor.run_id!r}, "
            f"consumer={consumer.run_id!r}"
        )
    ensure_connector_probe("synthesis")
    settings = get_settings()
    if settings.synthesis_mode == "deterministic":
        return _run_synthesis_deterministic(run_id, clinical, competitor, consumer)
    if not settings.openai_api_key:
        _log.info(
            "synthesis_mode=gpt but PHARMA_RD_OPENAI_API_KEY unset; "
            "using deterministic ranking (NFR-I1)",
            extra={
                "event": "synthesis_gpt_skipped",
                "outcome": "ok",
                "reason": "openai_api_key_unset",
            },
        )
        out = _run_synthesis_deterministic(run_id, clinical, competitor, consumer)
        note = (
            "GPT synthesis skipped: PHARMA_RD_OPENAI_API_KEY not set while "
            "PHARMA_RD_SYNTHESIS_MODE=gpt; used deterministic ranking (story 6.5). "
            "Set the key for GPT synthesis, or set "
            "PHARMA_RD_SYNTHESIS_MODE=deterministic."
        )
        return out.model_copy(
            update={
                "aggregated_upstream_gaps": [note, *out.aggregated_upstream_gaps],
            }
        )
    return _run_synthesis_gpt(run_id, clinical, competitor, consumer)
