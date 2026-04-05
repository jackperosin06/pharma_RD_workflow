"""OpenAI GPT insight report HTML + Markdown (story 7.6 / FR18, FR22)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, ValidationError

from pharma_rd.config import Settings
from pharma_rd.integrations.openai_client import (
    create_openai_client_for_report_delivery,
    run_chat_json_completion,
)
from pharma_rd.pipeline.contracts import SynthesisOutput

_SYSTEM_PROMPT = (
    "You are a senior pharmaceutical strategy consultant writing for {org}. "
    "Produce a CEO-ready insight report from the structured synthesis JSON. "
    "Respond with a single JSON object only, keys exactly: "
    '"report_html" (string), "report_markdown" (string), '
    '"slack_executive_excerpt" (string, optional, <=600 chars). '
    "report_html MUST be an HTML **fragment for the document body only** "
    "(no <!DOCTYPE>, no html/head/body wrapper): semantic sections with "
    "<section>, <article>, <h1>–<h3>, <p> (continuous prose for the executive "
    "summary—not bullet-only), narrative paragraphs for each ranked opportunity "
    "(use data from synthesis.ranked_opportunities), and a commercially framed "
    "conclusion section. "
    "Do not use <script> or inline event handlers. Prefer semantic tags; "
    "you may use limited inline style attributes for typography. "
    "You MUST include these exact compliance phrases verbatim in report_html "
    "and report_markdown: "
    "Executive: \"Human judgment (FR22): Items in this report are recommendations "
    "for review only—not approvals. Pursuit and portfolio decisions remain "
    "human-owned.\" "
    "Per opportunity: \"Recommendation only—not an approval. Pursuit is a human "
    "decision.\" "
    "Governance section must echo FR22 pursuit/governance themes from the product "
    "baseline. "
    "report_markdown must mirror report_html content as GitHub-flavored Markdown "
    "(headings, prose, fenced code only when needed). "
    "slack_executive_excerpt: one short prose blurb for chat notifications."
)


class GptReportDeliveryJson(BaseModel):
    """Model JSON object from OpenAI (story 7.6)."""

    model_config = ConfigDict(extra="forbid")

    report_html: str = ""
    report_markdown: str = ""
    slack_executive_excerpt: str = ""


@dataclass(frozen=True)
class GptReportDeliveryResult:
    report_html_fragment: str
    report_markdown: str
    slack_executive_excerpt: str


def _user_payload(
    settings: Settings,
    run_id: str,
    synthesis: SynthesisOutput,
) -> str:
    payload = {
        "run_id": run_id,
        "synthesis": synthesis.model_dump(mode="json"),
        "therapeutic_area_labels": settings.therapeutic_area_labels(),
        "competitor_watchlist_labels": settings.competitor_labels(),
        "insight_org_display_name": settings.insight_org_display_name,
        "deployment_profile": settings.deployment_profile,
    }
    return json.dumps(payload, ensure_ascii=False)


def call_gpt_report_delivery(
    settings: Settings,
    run_id: str,
    synthesis: SynthesisOutput,
) -> tuple[GptReportDeliveryResult | None, str | None]:
    """Call OpenAI; return (result, None) or (None, operator_error)."""
    if not settings.openai_api_key:
        return None, "missing_api_key"

    client = create_openai_client_for_report_delivery(settings)
    system = _SYSTEM_PROMPT.replace(
        "{org}", settings.insight_org_display_name
    )
    user_content = _user_payload(settings, run_id, synthesis)
    choice, err = run_chat_json_completion(
        client,
        model=settings.openai_model,
        system=system,
        user_content=user_content,
    )
    if err:
        return None, err
    if not choice or not choice.strip():
        return None, "empty_model_response"

    try:
        data = json.loads(choice)
    except json.JSONDecodeError as e:
        return None, f"json_decode: {e}"

    try:
        parsed = GptReportDeliveryJson.model_validate(data)
    except ValidationError as e:
        return None, f"validate: {e}"

    frag = (parsed.report_html or "").strip()
    md = (parsed.report_markdown or "").strip()
    if not frag or not md:
        return None, "empty_report_fields"

    def _visible_len(html: str, *, strip_tags: bool) -> int:
        t = html or ""
        if strip_tags:
            t = re.sub(r"<[^>]+>", " ", t)
        return len(re.sub(r"\s+", " ", t).strip())

    vis_html = _visible_len(frag, strip_tags=True)
    vis_md = _visible_len(md, strip_tags=False)
    if vis_html < 40 and vis_md < 40:
        return None, "thin_gpt_report"

    excerpt = (parsed.slack_executive_excerpt or "").strip()
    if len(excerpt) > 600:
        excerpt = excerpt[:599] + "…"

    return (
        GptReportDeliveryResult(
            report_html_fragment=frag,
            report_markdown=md,
            slack_executive_excerpt=excerpt,
        ),
        None,
    )
