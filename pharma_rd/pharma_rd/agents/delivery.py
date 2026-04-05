"""Delivery agent — FR18 Markdown report (Epic 7)."""

from __future__ import annotations

from html import escape
from pathlib import Path

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.config import Settings, get_settings
from pharma_rd.integrations.openai_report_delivery import call_gpt_report_delivery
from pharma_rd.integrations.report_distribution import distribute_insight_report
from pharma_rd.integrations.report_html_sanitize import sanitize_report_html_fragment
from pharma_rd.integrations.slack_insight_notification import (
    send_slack_insight_notification,
)
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.persistence.artifacts import write_utf8_artifact_atomic
from pharma_rd.pipeline.contracts import DeliveryOutput, SynthesisOutput

_log = get_pipeline_logger("pharma_rd.agents.delivery")

# FR22 — human-owned pursuit language (practice build; edit here for legal review).
_FR22_EXECUTIVE_PLAIN = (
    "Human judgment (FR22): Items in this report are recommendations for review "
    "only—not approvals. Pursuit and portfolio decisions remain human-owned."
)
_FR22_EXECUTIVE_MD = (
    "> **Human judgment (FR22):** Items in this report are **recommendations** "
    "for review only—not **approvals**. **Pursuit and portfolio decisions remain "
    "human-owned.**\n\n"
)
_FR22_PER_OPPORTUNITY_PLAIN = (
    "Recommendation only—not an approval. Pursuit is a human decision."
)
_FR22_PER_OPPORTUNITY_MD = (
    "> *Recommendation only—not an approval. Pursuit is a human decision.*\n\n"
)
_FR22_GOVERNANCE_PLAIN = (
    "This report presents recommendations derived from signals available to the "
    "workflow. It does not approve development, launch, or commercialization. "
    "Pursuit decisions remain with qualified human decision-makers and your "
    "organization's governance processes. Use this as input to judgment, not a "
    "substitute for it."
)
_FR22_GOVERNANCE_MD = (
    "This report presents **recommendations** derived from signals available to the "
    "workflow. It does **not** approve development, launch, or commercialization. "
    "**Pursuit decisions remain with qualified human decision-makers** and your "
    "organization's governance processes. Use this as input to judgment, not a "
    "substitute for it.\n"
)
_FR22_FOOTER_PLAIN = (
    "Recommendations, not approvals—pursuit decisions remain human-owned (FR22)."
)


def _fr26_deployment_run_summary(settings: Settings) -> tuple[str, str]:
    """Markdown + HTML fragments for FR26 when deployment profile is practice."""
    if settings.deployment_profile != "practice":
        return ("", "")
    md = (
        "- **Deployment (FR26):** Practice build — public/mock sources permitted; "
        "enterprise SSO is not required for this MVP (FR34 is roadmap).\n\n"
    )
    html = (
        "<p><strong>Deployment (FR26):</strong> Practice build — public/mock "
        "sources permitted; enterprise SSO is not required for this MVP "
        "(FR34 is roadmap).</p>\n"
    )
    return (md, html)


def _fence(text: str) -> str:
    """Fence free text so markdown metacharacters in upstream strings are contained."""
    safe = text.replace("```", "``\u200b`")
    return f"```text\n{safe}\n```\n"


def _md_heading_title(s: str) -> str:
    """Single-line title for ``###`` headings; avoids newlines and raw ``#`` breaks."""
    t = (s or "").replace("\n", " ").strip()
    return t.replace("#", "\\#")


def _render_markdown(run_id: str, syn: SynthesisOutput) -> str:
    settings = get_settings()
    fr26_md, _ = _fr26_deployment_run_summary(settings)
    lines: list[str] = []
    lines.append(f"# Insight report ({run_id})\n")
    lines.append("## Run summary\n")
    lines.append(_FR22_EXECUTIVE_MD)
    lines.append(fr26_md)
    lines.append(f"- **signal_characterization:** `{syn.signal_characterization}`\n")
    lines.append("- **scan_summary (FR28):**\n")
    if syn.scan_summary_lines:
        for s in syn.scan_summary_lines:
            lines.append(f"  - {s}\n")
    else:
        lines.append("  - *(none — legacy or empty synthesis)*\n")
    if syn.aggregated_upstream_gaps:
        lines.append("- **upstream gaps (preview):**\n")
        for g in syn.aggregated_upstream_gaps[:10]:
            lines.append(f"  - {g}\n")
        extra = len(syn.aggregated_upstream_gaps) - 10
        if extra > 0:
            lines.append(f"  - … ({extra} more)\n")
    lines.append("\n## Ranked opportunities\n")
    if not syn.ranked_opportunities:
        lines.append("(none)\n")
    else:
        for row in sorted(syn.ranked_opportunities, key=lambda r: r.rank):
            lines.append(
                f"### {row.rank}. {_md_heading_title(row.title)}\n"
            )
            lines.append(_FR22_PER_OPPORTUNITY_MD)
            lines.append("**Rationale**\n")
            lines.append(_fence(row.rationale_short))
            if row.evidence_references:
                lines.append("**Evidence references**\n")
                for er in row.evidence_references:
                    lines.append(
                        f"- **{er.domain}** — {er.label}: `{er.reference}`\n"
                    )
            lines.append("**Commercial viability**\n")
            lines.append(_fence(row.commercial_viability))
            lines.append("\n")
    lines.append("## Governance and disclaimer\n")
    lines.append(_FR22_GOVERNANCE_MD)
    return "".join(lines)


def _ensure_fr22_html_fragment(fragment: str) -> str:
    """Inject executive FR22 banner if model omitted required compliance text."""
    low = fragment.lower()
    if "human judgment" in low and "fr22" in low:
        return fragment
    return (
        '<section class="fr22-executive"><p><strong>Human judgment (FR22):</strong> '
        "Items in this report are recommendations for review only—not approvals. "
        "Pursuit and portfolio decisions remain human-owned.</p></section>\n"
        + fragment
    )


def _ensure_fr22_markdown(md: str) -> str:
    if "human judgment" in md.lower() and "fr22" in md.lower():
        return md
    return _FR22_EXECUTIVE_MD + md


def _wrap_gpt_html_fragment(run_id: str, inner: str, settings: Settings) -> str:
    """Trusted shell around sanitized GPT body fragment (story 7.6)."""
    _, fr26_html = _fr26_deployment_run_summary(settings)
    parts: list[str] = []
    parts.append("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n")
    parts.append('<meta charset="utf-8" />\n')
    parts.append(f"<title>Insight report ({escape(run_id)})</title>\n")
    parts.append(
        "<style>"
        "body{font-family:system-ui,Segoe UI,sans-serif;max-width:52rem;margin:1rem;"
        "line-height:1.45;}"
        "pre{white-space:pre-wrap;word-break:break-word;background:#f6f8fa;padding:0.5rem;}"
        "</style>\n</head>\n<body>\n"
    )
    parts.append(inner)
    parts.append("\n")
    parts.append(fr26_html)
    parts.append("</body>\n</html>\n")
    return "".join(parts)


def _render_html(run_id: str, syn: SynthesisOutput) -> str:
    """Parallel HTML view for NFR-P2 (open in any browser without extensions)."""
    settings = get_settings()
    _, fr26_html = _fr26_deployment_run_summary(settings)
    parts: list[str] = []
    parts.append("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n")
    parts.append('<meta charset="utf-8" />\n')
    parts.append(f"<title>Insight report ({escape(run_id)})</title>\n")
    parts.append(
        "<style>"
        "body{font-family:system-ui,Segoe UI,sans-serif;max-width:52rem;margin:1rem;"
        "line-height:1.45;}"
        "pre{white-space:pre-wrap;word-break:break-word;background:#f6f8fa;padding:0.5rem;}"
        "</style>\n</head>\n<body>\n"
    )
    parts.append(f"<h1>Insight report ({escape(run_id)})</h1>\n")
    parts.append("<h2>Run summary</h2>\n")
    parts.append(
        f"<blockquote><p>{escape(_FR22_EXECUTIVE_PLAIN)}</p></blockquote>\n"
    )
    parts.append(fr26_html)
    parts.append("<ul>\n")
    parts.append(
        "<li><strong>signal_characterization:</strong> "
        f"{escape(str(syn.signal_characterization))}</li>\n"
    )
    parts.append("<li><strong>scan_summary (FR28):</strong><ul>\n")
    if syn.scan_summary_lines:
        for s in syn.scan_summary_lines:
            parts.append(f"<li>{escape(s)}</li>\n")
    else:
        parts.append("<li><em>(none — legacy or empty synthesis)</em></li>\n")
    parts.append("</ul></li>\n")
    if syn.aggregated_upstream_gaps:
        parts.append("<li><strong>upstream gaps (preview):</strong><ul>\n")
        for g in syn.aggregated_upstream_gaps[:10]:
            parts.append(f"<li>{escape(g)}</li>\n")
        extra = len(syn.aggregated_upstream_gaps) - 10
        if extra > 0:
            parts.append(f"<li>… ({extra} more)</li>\n")
        parts.append("</ul></li>\n")
    parts.append("</ul>\n")
    parts.append("<h2>Ranked opportunities</h2>\n")
    if not syn.ranked_opportunities:
        parts.append("<p>(none)</p>\n")
    else:
        for row in sorted(syn.ranked_opportunities, key=lambda r: r.rank):
            parts.append(
                f"<h3>{escape(str(row.rank))}. {escape(row.title)}</h3>\n"
            )
            parts.append(
                f"<p><em>{escape(_FR22_PER_OPPORTUNITY_PLAIN)}</em></p>\n"
            )
            parts.append("<p><strong>Rationale</strong></p>\n")
            parts.append(f"<pre>{escape(row.rationale_short)}</pre>\n")
            if row.evidence_references:
                parts.append("<p><strong>Evidence references</strong></p>\n<ul>\n")
                for er in row.evidence_references:
                    parts.append(
                        "<li><strong>"
                        + escape(er.domain)
                        + "</strong> — "
                        + escape(er.label)
                        + ": "
                        + escape(er.reference)
                        + "</li>\n"
                    )
                parts.append("</ul>\n")
            parts.append("<p><strong>Commercial viability</strong></p>\n")
            parts.append(f"<pre>{escape(row.commercial_viability)}</pre>\n")
    parts.append("<h2>Governance and disclaimer</h2>\n")
    parts.append(f"<p>{escape(_FR22_GOVERNANCE_PLAIN)}</p>\n")
    parts.append("<footer>\n")
    parts.append(f"<p>{escape(_FR22_FOOTER_PLAIN)}</p>\n")
    parts.append("</footer>\n")
    parts.append("</body>\n</html>\n")
    return "".join(parts)


def run_delivery(
    run_id: str,
    synthesis: SynthesisOutput,
    artifact_root: Path,
) -> DeliveryOutput:
    """Write ``report.md`` and ``report.html``; return metadata for ``output.json``."""
    if synthesis.run_id and synthesis.run_id != run_id:
        raise ValueError(
            "run_id mismatch: expected "
            f"{run_id!r}, synthesis has {synthesis.run_id!r}"
        )
    ensure_connector_probe("delivery")
    settings = get_settings()
    gpt_excerpt: str | None = None
    body: str
    html_body: str

    use_gpt = settings.report_renderer == "gpt" and bool(settings.openai_api_key)
    if use_gpt:
        gpt_result, gpt_err = call_gpt_report_delivery(settings, run_id, synthesis)
        if gpt_result is not None:
            frag = sanitize_report_html_fragment(gpt_result.report_html_fragment)
            frag = _ensure_fr22_html_fragment(frag)
            body = _ensure_fr22_markdown(gpt_result.report_markdown)
            html_body = _wrap_gpt_html_fragment(run_id, frag, settings)
            if gpt_result.slack_executive_excerpt:
                gpt_excerpt = gpt_result.slack_executive_excerpt
        elif settings.report_gpt_fallback_on_error:
            _log.warning(
                "delivery GPT report failed; using template renderer",
                extra={
                    "event": "delivery_gpt_fallback",
                    "outcome": "ok",
                    "detail": gpt_err or "unknown",
                },
            )
            body = _render_markdown(run_id, synthesis)
            html_body = _render_html(run_id, synthesis)
        else:
            raise ValueError(
                "GPT report delivery failed and PHARMA_RD_REPORT_GPT_FALLBACK_ON_ERROR "
                f"is false: {gpt_err or 'unknown_error'}"
            )
    elif settings.report_renderer == "gpt" and not settings.openai_api_key:
        _log.warning(
            "PHARMA_RD_REPORT_RENDERER=gpt but PHARMA_RD_OPENAI_API_KEY is unset; "
            "using template renderer",
            extra={"event": "delivery_gpt_skipped_no_key", "outcome": "ok"},
        )
        body = _render_markdown(run_id, synthesis)
        html_body = _render_html(run_id, synthesis)
    else:
        body = _render_markdown(run_id, synthesis)
        html_body = _render_html(run_id, synthesis)

    rel, size = write_utf8_artifact_atomic(
        artifact_root,
        (run_id, "delivery", "report.md"),
        body,
    )
    rel_html, size_html = write_utf8_artifact_atomic(
        artifact_root,
        (run_id, "delivery", "report.html"),
        html_body,
    )
    _log.info(
        "delivery report written",
        extra={
            "event": "delivery_report_written",
            "outcome": "ok",
            "report_relative_path": rel,
            "report_byte_size": size,
            "report_html_relative_path": rel_html,
            "report_html_byte_size": size_html,
        },
    )
    slack_st, slack_det = send_slack_insight_notification(
        webhook_url=settings.slack_webhook_url,
        run_id=run_id,
        synthesis=synthesis,
        settings=settings,
        artifact_root=artifact_root,
        logger=_log,
        timeout_seconds=settings.slack_webhook_timeout_seconds,
        gpt_executive_excerpt=gpt_excerpt,
    )
    d_ch, d_st, d_det = distribute_insight_report(
        run_id,
        artifact_root,
        settings=settings,
        logger=_log,
    )
    return DeliveryOutput(
        schema_version=3,
        run_id=run_id,
        report_relative_path=rel,
        report_format="markdown",
        report_byte_size=size,
        report_html_relative_path=rel_html,
        report_html_byte_size=size_html,
        distribution_channel=d_ch,
        distribution_status=d_st,
        distribution_detail=d_det,
        slack_notify_status=slack_st,
        slack_notify_detail=slack_det,
    )
