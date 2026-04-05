"""Regulatory approvals/disclosures: fixtures and OpenFDA drugsfda (FR8, NFR-I1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from pharma_rd.config import Settings
from pharma_rd.http_client import request_with_retries
from pharma_rd.pipeline.contracts import (
    PatentFilingFlagItem,
    PipelineDisclosureItem,
    RegulatoryApprovalItem,
    RegulatoryDisclosureItem,
)


@dataclass(frozen=True)
class PipelineDisclosureCandidate:
    """Ingested pipeline_disclosures row before FR9 scope matching."""

    title: str
    summary: str
    reference: str
    observed_at: str
    source_label: str
    scope_tags: tuple[str, ...]


@dataclass(frozen=True)
class PatentFilingCandidate:
    """Ingested patent_filing_flags row before FR10 watchlist matching."""

    title: str
    summary: str
    reference: str
    observed_at: str
    source_label: str
    competitor_tags: tuple[str, ...]


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _parse_approval_obj(obj: object, hint: str) -> RegulatoryApprovalItem:
    if not isinstance(obj, dict):
        raise ValueError(f"approval entry must be object, got {type(obj).__name__}")
    title = obj.get("title")
    summary = obj.get("summary")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing or invalid approval title")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid approval summary")
    ref = obj.get("reference")
    ref_s = ref if isinstance(ref, str) and ref.strip() else hint
    label = obj.get("source_label")
    label_s = label if isinstance(label, str) and label.strip() else "fixture"
    obs = obj.get("observed_at")
    obs_s = obs if isinstance(obs, str) and obs.strip() else "1970-01-01T00:00:00Z"
    return RegulatoryApprovalItem(
        title=title.strip(),
        summary=summary.strip(),
        reference=ref_s.strip(),
        source_label=label_s.strip(),
        observed_at=obs_s.strip(),
    )


def _parse_disclosure_obj(obj: object, hint: str) -> RegulatoryDisclosureItem:
    if not isinstance(obj, dict):
        raise ValueError(f"disclosure entry must be object, got {type(obj).__name__}")
    title = obj.get("title")
    summary = obj.get("summary")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing or invalid disclosure title")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid disclosure summary")
    ref = obj.get("reference")
    ref_s = ref if isinstance(ref, str) and ref.strip() else hint
    label = obj.get("source_label")
    label_s = label if isinstance(label, str) and label.strip() else "fixture"
    obs = obj.get("observed_at")
    obs_s = obs if isinstance(obs, str) and obs.strip() else "1970-01-01T00:00:00Z"
    return RegulatoryDisclosureItem(
        title=title.strip(),
        summary=summary.strip(),
        reference=ref_s.strip(),
        source_label=label_s.strip(),
        observed_at=obs_s.strip(),
    )


def _parse_pipeline_disclosure_obj(
    obj: object,
    hint: str,
) -> PipelineDisclosureCandidate:
    if not isinstance(obj, dict):
        raise ValueError(
            f"pipeline_disclosures entry must be object, got {type(obj).__name__}"
        )
    title = obj.get("title")
    summary = obj.get("summary")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing or invalid pipeline_disclosure title")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid pipeline_disclosure summary")
    ref = obj.get("reference")
    ref_s = ref if isinstance(ref, str) and ref.strip() else hint
    label = obj.get("source_label")
    label_s = label if isinstance(label, str) and label.strip() else "fixture"
    obs = obj.get("observed_at")
    obs_s = obs if isinstance(obs, str) and obs.strip() else "1970-01-01T00:00:00Z"
    raw_tags = obj.get("scope_tags")
    if raw_tags is None:
        raise ValueError("pipeline_disclosures entry requires \"scope_tags\" array")
    if not isinstance(raw_tags, list):
        raise ValueError('"scope_tags" must be an array of strings')
    tags: list[str] = []
    for i, t in enumerate(raw_tags):
        if not isinstance(t, str) or not t.strip():
            raise ValueError(f"scope_tags[{i}] must be a non-empty string")
        tags.append(t.strip())
    return PipelineDisclosureCandidate(
        title=title.strip(),
        summary=summary.strip(),
        reference=ref_s.strip(),
        source_label=label_s.strip(),
        observed_at=obs_s.strip(),
        scope_tags=tuple(tags),
    )


def _parse_patent_filing_obj(obj: object, hint: str) -> PatentFilingCandidate:
    if not isinstance(obj, dict):
        raise ValueError(
            f"patent_filing_flags entry must be object, got {type(obj).__name__}"
        )
    title = obj.get("title")
    summary = obj.get("summary")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing or invalid patent_filing_flags title")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid patent_filing_flags summary")
    ref = obj.get("reference")
    ref_s = ref if isinstance(ref, str) and ref.strip() else hint
    label = obj.get("source_label")
    label_s = label if isinstance(label, str) and label.strip() else "fixture"
    obs = obj.get("observed_at")
    obs_s = obs if isinstance(obs, str) and obs.strip() else "1970-01-01T00:00:00Z"
    raw_tags = obj.get("competitor_tags")
    tags: list[str] = []
    if raw_tags is None:
        pass
    elif isinstance(raw_tags, list):
        for i, t in enumerate(raw_tags):
            if not isinstance(t, str) or not t.strip():
                raise ValueError(f"competitor_tags[{i}] must be a non-empty string")
            tags.append(t.strip())
    else:
        raise ValueError('"competitor_tags" must be an array of strings or omitted')
    return PatentFilingCandidate(
        title=title.strip(),
        summary=summary.strip(),
        reference=ref_s.strip(),
        source_label=label_s.strip(),
        observed_at=obs_s.strip(),
        competitor_tags=tuple(tags),
    )


def _load_one_fixture_file(
    path: Path,
    *,
    max_bytes: int,
) -> tuple[
    list[RegulatoryApprovalItem],
    list[RegulatoryDisclosureItem],
    list[PipelineDisclosureCandidate],
    list[PatentFilingCandidate],
    list[str],
]:
    gaps: list[str] = []
    try:
        st = path.stat()
    except OSError as e:
        return [], [], [], [], [f"Competitor regulatory: cannot stat {path}: {e}"]
    if st.st_size > max_bytes:
        return [], [], [], [], [
            f"Competitor regulatory: skipped {path.name} "
            f"(size {st.st_size} exceeds max {max_bytes} bytes)."
        ]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [], [], [], [], [f"Competitor regulatory: cannot read {path}: {e}"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        msg = f"Competitor regulatory: invalid JSON in {path.name}: {e}"
        return [], [], [], [], [msg]
    if not isinstance(data, dict):
        return [], [], [], [], [
            f"Competitor regulatory: root in {path.name} must be a JSON object "
            'with optional "approvals", "disclosures", "pipeline_disclosures", '
            'and "patent_filing_flags".'
        ]
    approvals: list[RegulatoryApprovalItem] = []
    disclosures: list[RegulatoryDisclosureItem] = []
    pipeline: list[PipelineDisclosureCandidate] = []
    patents: list[PatentFilingCandidate] = []
    hint = str(path)
    try:
        raw_a = data.get("approvals")
        if raw_a is not None:
            if not isinstance(raw_a, list):
                msg = (
                    f'Competitor regulatory: "approvals" in {path.name} '
                    "must be an array."
                )
                return [], [], [], [], [msg]
            for i, el in enumerate(raw_a):
                approvals.append(_parse_approval_obj(el, f"{hint}#approvals[{i}]"))
        raw_d = data.get("disclosures")
        if raw_d is not None:
            if not isinstance(raw_d, list):
                return [], [], [], [], [
                    f'Competitor regulatory: "disclosures" in {path.name} '
                    "must be an array."
                ]
            for i, el in enumerate(raw_d):
                tag = f"{hint}#disclosures[{i}]"
                disclosures.append(_parse_disclosure_obj(el, tag))
        raw_p = data.get("pipeline_disclosures")
        if raw_p is not None:
            if not isinstance(raw_p, list):
                return [], [], [], [], [
                    f'Competitor regulatory: "pipeline_disclosures" in {path.name} '
                    "must be an array."
                ]
            for i, el in enumerate(raw_p):
                tag = f"{hint}#pipeline_disclosures[{i}]"
                pipeline.append(_parse_pipeline_disclosure_obj(el, tag))
        raw_pf = data.get("patent_filing_flags")
        if raw_pf is not None:
            if not isinstance(raw_pf, list):
                return [], [], [], [], [
                    f'Competitor regulatory: "patent_filing_flags" in {path.name} '
                    "must be an array."
                ]
            for i, el in enumerate(raw_pf):
                tag = f"{hint}#patent_filing_flags[{i}]"
                patents.append(_parse_patent_filing_obj(el, tag))
    except ValueError as e:
        return [], [], [], [], [f"Competitor regulatory: {path.name}: {e}"]
    return approvals, disclosures, pipeline, patents, gaps


def filter_pipeline_disclosures(
    candidates: list[PipelineDisclosureCandidate],
    scope_labels: list[str],
    *,
    fixture_path_configured: bool,
) -> tuple[list[PipelineDisclosureItem], list[str]]:
    """
    Match pipeline rows to configured watch scopes (case-insensitive tag match).

    Returns (items, integration_notes_to_append).
    """
    if not scope_labels:
        return [], []
    scope_pairs: list[tuple[str, str]] = []
    for s in scope_labels:
        s = s.strip()
        if s:
            scope_pairs.append((s.lower(), s))
    if not scope_pairs:
        return [], []

    if not fixture_path_configured:
        joined = ", ".join(s for _, s in scope_pairs)
        return [], [
            "Pipeline disclosure (FR9): no JSON rows loaded; configure "
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH with a \"pipeline_disclosures\" "
            f"array (watch scopes: {joined})."
        ]

    out: list[PipelineDisclosureItem] = []
    for c in candidates:
        tag_lower = {t.lower().strip() for t in c.scope_tags}
        matched_display: str | None = None
        for low, display in scope_pairs:
            if low in tag_lower:
                matched_display = display
                break
        if matched_display is not None:
            out.append(
                PipelineDisclosureItem(
                    title=c.title,
                    summary=c.summary,
                    reference=c.reference,
                    source_label=c.source_label,
                    observed_at=c.observed_at,
                    matched_scope=matched_display,
                )
            )

    if not out:
        joined = ", ".join(s for _, s in scope_pairs)
        return [], [
            "Pipeline disclosure (FR9): none found for configured watch scopes: "
            f"{joined}."
        ]
    return out, []


def filter_patent_filing_flags(
    candidates: list[PatentFilingCandidate],
    labels: list[str],
    *,
    fixture_path_configured: bool,
) -> tuple[list[PatentFilingFlagItem], list[str]]:
    """
    Match patent rows to configured competitor watchlist (case-insensitive).

    Empty ``competitor_tags`` on a row applies to the first configured label.
    """
    label_pairs: list[tuple[str, str]] = []
    for x in labels:
        x = x.strip()
        if x:
            label_pairs.append((x.lower(), x))

    if not label_pairs:
        return [], [
            "Patent filing flags (FR10): not evaluated without competitor watchlist "
            "(PHARMA_RD_COMPETITOR_WATCHLIST empty)."
        ]

    if not fixture_path_configured:
        joined = ", ".join(disp for _, disp in label_pairs)
        return [], [
            "Patent filing flags (FR10): no JSON rows loaded; configure "
            "PHARMA_RD_COMPETITOR_REGULATORY_PATH with a \"patent_filing_flags\" "
            f"array (watchlist: {joined})."
        ]

    out: list[PatentFilingFlagItem] = []
    for c in candidates:
        tags_lower = {t.lower().strip() for t in c.competitor_tags}
        matched: str | None = None
        if not c.competitor_tags:
            matched = label_pairs[0][1]
        else:
            for low, display in label_pairs:
                if low in tags_lower:
                    matched = display
                    break
        if matched is not None:
            out.append(
                PatentFilingFlagItem(
                    title=c.title,
                    summary=c.summary,
                    reference=c.reference,
                    source_label=c.source_label,
                    observed_at=c.observed_at,
                    matched_competitor=matched,
                )
            )

    if not out:
        joined = ", ".join(disp for _, disp in label_pairs)
        return [], [
            "Patent filing flags (FR10): none found for configured competitors: "
            f"{joined}."
        ]
    return out, []


def ingest_competitor_regulatory_fixture(
    settings: Settings,
) -> tuple[
    list[RegulatoryApprovalItem],
    list[RegulatoryDisclosureItem],
    list[PipelineDisclosureCandidate],
    list[PatentFilingCandidate],
    list[str],
    list[str],
]:
    """
    Load approvals/disclosures/pipeline/patent rows from configured JSON path.

    Returns (approvals, disclosures, pipeline_candidates, patent_candidates,
    integration_notes, data_gaps). Never raises for I/O or parse issues.
    """
    raw = settings.competitor_regulatory_path
    if raw is None:
        return (
            [],
            [],
            [],
            [],
            [],
            [],
        )

    path = _resolve_config_path(str(raw))
    max_b = settings.competitor_regulatory_max_file_bytes
    approvals: list[RegulatoryApprovalItem] = []
    disclosures: list[RegulatoryDisclosureItem] = []
    pipeline: list[PipelineDisclosureCandidate] = []
    patents: list[PatentFilingCandidate] = []
    notes: list[str] = []
    gaps: list[str] = []

    if not path.exists():
        msg = f"Competitor regulatory path does not exist: {path}"
        return [], [], [], [], [], [msg]

    if path.is_file():
        a, d, p, pf, g = _load_one_fixture_file(path, max_bytes=max_b)
        approvals.extend(a)
        disclosures.extend(d)
        pipeline.extend(p)
        patents.extend(pf)
        gaps.extend(g)
        if a or d or p or pf:
            notes.append(
                f"Competitor regulatory: loaded fixture from {path.name} "
                f"({len(a)} approval(s), {len(d)} disclosure(s), "
                f"{len(p)} pipeline_disclosure(s), {len(pf)} patent_filing_flag(s))."
            )
        return approvals, disclosures, pipeline, patents, notes, gaps

    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        if not json_files:
            gaps.append(
                f"Competitor regulatory directory {path} contains no *.json files."
            )
            return [], [], [], [], [], gaps
        for jp in json_files:
            a, d, p, pf, g = _load_one_fixture_file(jp, max_bytes=max_b)
            approvals.extend(a)
            disclosures.extend(d)
            pipeline.extend(p)
            patents.extend(pf)
            gaps.extend(g)
        if approvals or disclosures or pipeline or patents:
            notes.append(
                f"Competitor regulatory: loaded {len(approvals)} approval(s), "
                f"{len(disclosures)} disclosure(s), {len(pipeline)} "
                f"pipeline_disclosure(s), and {len(patents)} patent_filing_flag(s) "
                f"from {len(json_files)} file(s) under {path.name}/."
            )
        return approvals, disclosures, pipeline, patents, notes, gaps

    gaps.append(f"Competitor regulatory path is not a file or directory: {path}")
    return [], [], [], [], [], gaps


def _observed_at_from_drugsfda_submissions(obj: dict) -> str | None:
    """Best-effort ISO 8601 UTC from OpenFDA submission_status_date (often YYYYMMDD)."""
    subs = obj.get("submissions")
    if not isinstance(subs, list):
        return None
    parsed: list[str] = []
    for s in subs:
        if not isinstance(s, dict):
            continue
        d = s.get("submission_status_date")
        if not isinstance(d, str) or not d.strip():
            continue
        ds = d.strip()
        if len(ds) == 8 and ds.isdigit():
            parsed.append(f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}T00:00:00Z")
        elif "T" in ds:
            p = ds if ds.endswith("Z") else f"{ds}Z"
            parsed.append(p)
    if not parsed:
        return None
    return max(parsed)


def _build_openfda_sponsor_search(labels: list[str]) -> str:
    parts: list[str] = []
    for label in labels:
        esc = label.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'openfda.sponsor_name:"{esc}"')
    return " OR ".join(f"({p})" for p in parts)


def _map_drugsfda_result(obj: object) -> tuple[RegulatoryApprovalItem | None, bool]:
    """Returns (item, True) if observed_at fell back (no parseable submission date)."""
    if not isinstance(obj, dict):
        return None, False
    sponsor = obj.get("sponsor_name")
    sp = sponsor.strip() if isinstance(sponsor, str) else "Unknown sponsor"
    products = obj.get("products")
    brand = ""
    if isinstance(products, list) and products:
        p0 = products[0]
        if isinstance(p0, dict):
            brand = (
                p0.get("brand_name")
                or p0.get("marketing_status")
                or p0.get("dosage_form")
                or ""
            )
            if isinstance(brand, str):
                brand = brand.strip()
            else:
                brand = ""
    title = f"{brand} ({sp})".strip(" ()") if brand else sp
    summary = (
        f"OpenFDA drugsfda record for sponsor {sp}. "
        "See reference for FDA application context (MVP summary)."
    )
    app_no = obj.get("application_number")
    if isinstance(app_no, str) and app_no.strip():
        ref = (
            "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?"
            f"event=overview.process&ApplNo={app_no.strip()}"
        )
    else:
        ref = "https://open.fda.gov/apis/drug/drugsfda/"
    parsed_obs = _observed_at_from_drugsfda_submissions(obj)
    fallback_obs = parsed_obs is None
    observed_at = parsed_obs if parsed_obs is not None else "1970-01-01T00:00:00Z"
    return (
        RegulatoryApprovalItem(
            title=title[:500],
            summary=summary[:2000],
            reference=ref,
            source_label="openfda",
            observed_at=observed_at,
        ),
        fallback_obs,
    )


def fetch_openfda_approvals(
    labels: list[str],
    *,
    settings: Settings,
) -> tuple[list[RegulatoryApprovalItem], list[str], list[str]]:
    """
    Query OpenFDA drugsfda for sponsor names matching watchlist labels.

    Returns (approval_items, integration_notes, data_gaps). Raises ConnectorFailure
    on HTTP failures after retries (NFR-I2 via runner).
    """
    if not labels:
        return [], [], ["OpenFDA query skipped: empty competitor watchlist."]
    search = _build_openfda_sponsor_search(labels)
    limit = settings.openfda_max_results
    raw = settings.openfda_drugsfda_url.strip()
    base = raw.split("?")[0].rstrip("/")
    if not base:
        base = "https://api.fda.gov/drug/drugsfda.json"
    url = f"{base}?{urlencode({'search': search, 'limit': str(limit)})}"

    resp = request_with_retries("GET", url, stage_key="competitor")
    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        return (
            [],
            [],
            [f"OpenFDA returned non-JSON body: {e}"],
        )

    notes: list[str] = [f"OpenFDA drugsfda query: {search!r} (limit {limit})."]

    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        msg = err.get("message", err) if isinstance(err, dict) else err
        return [], [], [f"OpenFDA error response: {msg}"]

    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return (
            [],
            notes,
            ["OpenFDA response missing \"results\" array; no approvals parsed."],
        )

    items: list[RegulatoryApprovalItem] = []
    any_fallback_obs = False
    for raw in results:
        mapped, fallback_obs = _map_drugsfda_result(raw)
        if mapped is not None:
            items.append(mapped)
            if fallback_obs:
                any_fallback_obs = True

    if not items:
        notes.append("No drugsfda results returned for this watchlist (empty set).")
    gaps: list[str] = []
    if items and any_fallback_obs:
        gaps.append(
            "OpenFDA: one or more drugsfda records had no parseable "
            "submission_status_date; observed_at may be a placeholder epoch."
        )
    return items, notes, gaps
