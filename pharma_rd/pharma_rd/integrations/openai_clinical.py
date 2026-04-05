"""OpenAI GPT-4o clinical analyst pass (story 3.3 / FR6 extension)."""

from __future__ import annotations

import json
from typing import Any

from pharma_rd.config import Settings
from pharma_rd.integrations.openai_client import (
    create_openai_client,
    run_chat_json_completion,
)
from pharma_rd.pipeline.contracts import ClinicalGptAnalysis, ClinicalOutput

_SYSTEM_PROMPT_TEMPLATE = (
    "You are an expert pharmaceutical R&D analyst supporting {org}. "
    "You receive structured publication and internal-research summaries from "
    "monitoring pipelines (non-PHI, decision-support context). "
    "Assess what is clinically significant, relevance to the configured "
    "therapeutic areas, "
    "and which trials or signals {org} should prioritize for attention. "
    "Respond with a single JSON object only, using exactly these keys: "
    '"analyst_summary" (string), "ta_relevance_assessment" (string), '
    '"priority_trials_attention" (array of short strings identifying '
    "trials/topics to watch). "
    "Be concise and operational; do not invent PMIDs or URLs not present in the input."
)


def _payload_for_prompt(out: ClinicalOutput) -> dict[str, Any]:
    pubs = [
        {
            "title": p.title,
            "summary": p.summary,
            "reference": p.reference,
            "source": p.source,
        }
        for p in out.publication_items
    ]
    ir = [
        {
            "title": i.title,
            "summary": i.summary,
            "reference": i.reference,
            "source_label": i.source_label,
        }
        for i in out.internal_research_items
    ]
    return {
        "therapeutic_areas_configured": out.therapeutic_areas_configured,
        "publication_items": pubs,
        "internal_research_items": ir,
        "data_gaps": out.data_gaps,
    }


def call_clinical_gpt_analysis(
    settings: Settings,
    out: ClinicalOutput,
) -> tuple[ClinicalGptAnalysis | None, str | None]:
    """Call OpenAI; return (analysis, None) or (None, error_message_for_operator)."""
    key = settings.openai_api_key
    if not key:
        return None, "missing_api_key"

    client = create_openai_client(settings)
    system = _SYSTEM_PROMPT_TEMPLATE.format(org=settings.insight_org_display_name)
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

    summary = str(data.get("analyst_summary", "") or "").strip()
    ta_rel = str(data.get("ta_relevance_assessment", "") or "").strip()
    raw_pri = data.get("priority_trials_attention", [])
    if isinstance(raw_pri, list):
        priority = [str(x).strip() for x in raw_pri if str(x).strip()]
    else:
        priority = []

    return (
        ClinicalGptAnalysis(
            analyst_summary=summary,
            ta_relevance_assessment=ta_rel,
            priority_trials_attention=priority[:50],
        ),
        None,
    )
