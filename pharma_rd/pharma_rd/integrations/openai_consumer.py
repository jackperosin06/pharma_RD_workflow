"""OpenAI GPT-4o consumer / market analyst pass (story 5.4 / FR11–FR13)."""

from __future__ import annotations

import json
from typing import Any

from pharma_rd.config import Settings
from pharma_rd.integrations.openai_client import (
    create_openai_client,
    run_chat_json_completion,
)
from pharma_rd.pipeline.contracts import ConsumerGptAnalysis, ConsumerOutput


def _system_prompt(settings: Settings, out: ConsumerOutput) -> str:
    org = settings.insight_org_display_name
    practice = (
        "This run uses PRACTICE or MOCK consumer inputs (non-PHI, decision-support "
        "only). Do not treat narratives as real patient data or regulatory evidence. "
        "Stay concise and avoid overconfidence."
        if out.practice_mode
        else (
            "Inputs are configured fixtures or feeds assumed non-PHI for MVP "
            "(NFR-S4). Do not infer PHI."
        )
    )
    return (
        f"You are an expert pharmaceutical market analyst supporting {org}. "
        f"{practice} "
        "You receive structured consumer and market signals: feedback themes, "
        "pharmacy sales trends, and unmet-need / demand signals. "
        "Surface unmet needs, demand patterns, and relevance to line-extension "
        f"opportunities from {org}'s perspective. "
        "Respond with a single JSON object only, using exactly these keys: "
        '"unmet_need_synthesis" (string), '
        '"demand_pattern_summary" (string), '
        '"line_extension_relevance" (string). '
        "Be concise and operational; do not invent sources not present in the input."
    )


def _payload_for_prompt(out: ConsumerOutput) -> dict[str, Any]:
    themes = [
        {"theme": t.theme, "summary": t.summary, "source": t.source}
        for t in out.feedback_themes
    ]
    sales = [
        {
            "summary": s.summary,
            "scope": s.scope,
            "period": s.period,
            "source": s.source,
        }
        for s in out.pharmacy_sales_trends
    ]
    demand = [
        {"signal": d.signal, "summary": d.summary, "source": d.source}
        for d in out.unmet_need_demand_signals
    ]
    return {
        "practice_mode": out.practice_mode,
        "feedback_themes": themes,
        "pharmacy_sales_trends": sales,
        "unmet_need_demand_signals": demand,
        "data_gaps": out.data_gaps,
    }


def call_consumer_gpt_analysis(
    settings: Settings,
    out: ConsumerOutput,
) -> tuple[ConsumerGptAnalysis | None, str | None]:
    """Call OpenAI; return (analysis, None) or (None, error_message_for_operator)."""
    key = settings.openai_api_key
    if not key:
        return None, "missing_api_key"

    client = create_openai_client(settings)
    system = _system_prompt(settings, out)
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

    unmet = str(data.get("unmet_need_synthesis", "") or "").strip()
    demand_s = str(data.get("demand_pattern_summary", "") or "").strip()
    line_ext = str(data.get("line_extension_relevance", "") or "").strip()

    return (
        ConsumerGptAnalysis(
            unmet_need_synthesis=unmet,
            demand_pattern_summary=demand_s,
            line_extension_relevance=line_ext,
        ),
        None,
    )
