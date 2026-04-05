"""OpenAI GPT-4o competitor intelligence pass (story 4.4 / FR8–FR10 extension)."""

from __future__ import annotations

import json
from typing import Any

from pharma_rd.config import Settings
from pharma_rd.integrations.openai_client import (
    create_openai_client,
    run_chat_json_completion,
)
from pharma_rd.pipeline.contracts import (
    CompetitorGptAnalysis,
    CompetitorOutput,
    UrgentAttentionSeverity,
)


def _system_prompt(settings: Settings) -> str:
    org = settings.insight_org_display_name
    labels = settings.competitor_labels()
    scopes = settings.pipeline_disclosure_scope_labels()
    obs = settings.competitor_observation_days
    watch = ", ".join(labels) if labels else "(none configured)"
    pscopes = ", ".join(scopes) if scopes else "(none configured)"
    return (
        f"You are an expert pharmaceutical competitive intelligence analyst supporting "
        f"{org}. "
        f"Configured competitor watchlist labels: {watch}. "
        f"Pipeline disclosure watch scopes: {pscopes}. "
        f"Observation window for this run: last {obs} calendar day(s) "
        f"(UTC; MVP may use coarse item dates). "
        "You receive structured regulatory and competitive signals (approvals, "
        "disclosures, pipeline disclosures, patent filing flags) from monitoring "
        "pipelines (non-PHI, decision-support context). "
        "Highlight strategic significance, threats and opportunities, and anything "
        f"needing urgent attention from {org}'s perspective. "
        "Respond with a single JSON object only, using exactly these keys: "
        '"strategic_commentary" (string), '
        '"threat_opportunity_themes" (array of short strings), '
        '"urgent_attention_flag" (boolean), '
        '"urgent_attention_items" (array of short strings), '
        '"urgent_attention_severity" (one of: none, low, medium, high). '
        "Be concise; do not invent approval numbers or URLs not present in the input."
    )


def _payload_for_prompt(out: CompetitorOutput) -> dict[str, Any]:
    approvals = [
        {
            "title": a.title,
            "summary": a.summary,
            "reference": a.reference,
            "source_label": a.source_label,
            "observed_at": a.observed_at,
        }
        for a in out.approval_items
    ]
    disclosures = [
        {
            "title": d.title,
            "summary": d.summary,
            "reference": d.reference,
            "source_label": d.source_label,
            "observed_at": d.observed_at,
        }
        for d in out.disclosure_items
    ]
    pipeline = [
        {
            "title": p.title,
            "summary": p.summary,
            "reference": p.reference,
            "source_label": p.source_label,
            "observed_at": p.observed_at,
            "matched_scope": p.matched_scope,
        }
        for p in out.pipeline_disclosure_items
    ]
    patents = [
        {
            "title": x.title,
            "summary": x.summary,
            "reference": x.reference,
            "source_label": x.source_label,
            "observed_at": x.observed_at,
            "matched_competitor": x.matched_competitor,
        }
        for x in out.patent_filing_flags
    ]
    return {
        "approval_items": approvals,
        "disclosure_items": disclosures,
        "pipeline_disclosure_items": pipeline,
        "patent_filing_flags": patents,
        "data_gaps": out.data_gaps,
    }


def _parse_severity(raw: object) -> UrgentAttentionSeverity:
    s = str(raw or "none").strip().lower()
    if s in ("none", "low", "medium", "high"):
        return s  # type: ignore[return-value]
    return "none"


def call_competitor_gpt_analysis(
    settings: Settings,
    out: CompetitorOutput,
) -> tuple[CompetitorGptAnalysis | None, str | None]:
    """Call OpenAI; return (analysis, None) or (None, error_message_for_operator)."""
    key = settings.openai_api_key
    if not key:
        return None, "missing_api_key"

    client = create_openai_client(settings)
    system = _system_prompt(settings)
    user_content = json.dumps(_payload_for_prompt(out), ensure_ascii=False)
    choice, err = run_chat_json_completion(
        client,
        model=settings.openai_model,
        system=system,
        user_content=user_content,
    )
    if err:
        return None, err

    try:
        data: dict[str, Any] = json.loads(choice)
    except json.JSONDecodeError as e:
        return None, f"invalid_json: {e}"

    commentary = str(data.get("strategic_commentary", "") or "").strip()
    raw_themes = data.get("threat_opportunity_themes", [])
    if isinstance(raw_themes, list):
        themes = [str(x).strip() for x in raw_themes if str(x).strip()]
    else:
        themes = []
    urgent_flag = bool(data.get("urgent_attention_flag", False))
    raw_urgent = data.get("urgent_attention_items", [])
    if isinstance(raw_urgent, list):
        urgent_items = [str(x).strip() for x in raw_urgent if str(x).strip()]
    else:
        urgent_items = []
    severity = _parse_severity(data.get("urgent_attention_severity"))

    return (
        CompetitorGptAnalysis(
            strategic_commentary=commentary,
            threat_opportunity_themes=themes[:50],
            urgent_attention_flag=urgent_flag,
            urgent_attention_items=urgent_items[:50],
            urgent_attention_severity=severity,
        ),
        None,
    )
