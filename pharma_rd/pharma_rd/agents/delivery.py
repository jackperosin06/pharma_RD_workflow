"""Delivery agent — FR18 Markdown report (Epic 7)."""

from __future__ import annotations

from pathlib import Path

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.config import Settings, get_settings
from pharma_rd.integrations.insight_report_html import (
    build_insight_report_html,
    wrap_gpt_body_as_document,
)
from pharma_rd.integrations.openai_report_delivery import call_gpt_report_delivery
from pharma_rd.integrations.report_distribution import distribute_insight_report
from pharma_rd.integrations.report_docx import build_insight_report_docx
from pharma_rd.integrations.report_executive_framing import prepare_run_summary_for_report
from pharma_rd.integrations.report_html_sanitize import sanitize_report_html_fragment
from pharma_rd.integrations.report_pdf import render_pdf_from_html
from pharma_rd.integrations.slack_insight_notification import (
    send_slack_insight_notification,
)
from pharma_rd.integrations.slack_pdf_upload import (
    upload_file_to_slack_channel,
    upload_report_pdf_to_slack,
)
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.persistence.artifacts import (
    read_stage_artifact_model,
    write_bytes_artifact_atomic,
    write_utf8_artifact_atomic,
)
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    DeliveryOutput,
    SlackPdfUploadStatus,
    SynthesisOutput,
)

_log = get_pipeline_logger("pharma_rd.agents.delivery")


def _therapeutic_areas_for_slack(
    artifact_root: Path, run_id: str, settings: Settings
) -> list[str]:
    """Prefer clinical artifact TA scope (same as the run); fall back to settings."""
    try:
        clinical = read_stage_artifact_model(
            artifact_root, run_id, "clinical", ClinicalOutput
        )
        return clinical.therapeutic_areas_configured
    except (FileNotFoundError, ValueError, OSError) as e:
        _log.warning(
            "slack TA scope: clinical artifact missing or invalid; using settings",
            extra={
                "event": "slack_ta_scope_fallback",
                "outcome": "ok",
                "detail": str(e)[:200],
            },
        )
        return settings.therapeutic_area_labels()

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
    rsum = prepare_run_summary_for_report(syn)
    lines: list[str] = []
    lines.append(f"# Insight report ({run_id})\n")
    lines.append("## Run summary\n")
    lines.append(_FR22_EXECUTIVE_MD)
    lines.append(fr26_md)
    lines.append(f"- **signal_characterization:** `{syn.signal_characterization}`\n")
    lines.append("- **Monitoring snapshot (FR28):**\n")
    if rsum.humanized_scan_lines:
        for s in rsum.humanized_scan_lines:
            lines.append(f"  - {s}\n")
    else:
        lines.append("  - *(none — legacy or empty synthesis)*\n")
    if rsum.coverage_gap_lines:
        lines.append("- **Coverage and configuration gaps (preview):**\n")
        for g in rsum.coverage_gap_lines:
            lines.append(f"  - {g}\n")
        if rsum.coverage_remaining:
            lines.append(f"  - … ({rsum.coverage_remaining} more)\n")
    if rsum.operator_gap_lines:
        lines.append("- **Technical pipeline notes (operators):**\n")
        lines.append(
            "  - *Internal telemetry for this run; JSON artifacts hold full detail.*\n"
        )
        for g in rsum.operator_gap_lines:
            lines.append(f"  - {g}\n")
        if rsum.operator_remaining:
            lines.append(f"  - … ({rsum.operator_remaining} more)\n")
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


def _gpt_fr26_block(settings: Settings) -> str:
    _, fr26_html = _fr26_deployment_run_summary(settings)
    if not fr26_html.strip():
        return ""
    return f'<div class="fr26-banner">{fr26_html}</div>'


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
            html_body = wrap_gpt_body_as_document(
                run_id, frag, settings, _gpt_fr26_block(settings)
            )
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
            _, fr26_html = _fr26_deployment_run_summary(settings)
            html_body = build_insight_report_html(
                run_id, synthesis, settings, fr26_html
            )
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
        _, fr26_html = _fr26_deployment_run_summary(settings)
        html_body = build_insight_report_html(run_id, synthesis, settings, fr26_html)
    else:
        body = _render_markdown(run_id, synthesis)
        _, fr26_html = _fr26_deployment_run_summary(settings)
        html_body = build_insight_report_html(run_id, synthesis, settings, fr26_html)

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
    docx_rel = ""
    docx_size = 0
    docx_st: SlackPdfUploadStatus = "skipped"
    docx_det = ""
    if settings.report_docx_enabled:
        try:
            docx_bytes = build_insight_report_docx(run_id, synthesis, settings)
            docx_rel, docx_size = write_bytes_artifact_atomic(
                artifact_root,
                (run_id, "delivery", "report.docx"),
                docx_bytes,
            )
        except Exception as e:
            _log.warning(
                "delivery docx render failed",
                extra={
                    "event": "delivery_docx_failed",
                    "outcome": "ok",
                    "detail": str(e)[:300],
                    "error_type": type(e).__name__,
                },
            )
        else:
            docx_st, docx_det = upload_file_to_slack_channel(
                settings=settings,
                file_bytes=docx_bytes,
                filename=f"insight-report-{run_id}.docx",
                initial_comment=(
                    f"Weekly insight report (Word) for run `{run_id}` — same structure "
                    "as report.md / report.html."
                ),
                logger=_log,
                timeout_seconds=settings.slack_pdf_upload_timeout_seconds,
            )
    pdf_rel = ""
    pdf_size = 0
    pdf_st: SlackPdfUploadStatus = "skipped"
    pdf_det = ""
    if settings.report_pdf_enabled:
        try:
            pdf_bytes = render_pdf_from_html(html_body)
            pdf_rel, pdf_size = write_bytes_artifact_atomic(
                artifact_root,
                (run_id, "delivery", "report.pdf"),
                pdf_bytes,
            )
        except (RuntimeError, OSError, ImportError) as e:
            # WeasyPrint: OSError if GLib/Pango/Cairo missing on the host.
            _log.warning(
                "delivery pdf render failed",
                extra={
                    "event": "delivery_pdf_failed",
                    "outcome": "ok",
                    "detail": str(e)[:300],
                    "error_type": type(e).__name__,
                },
            )
        else:
            pdf_st, pdf_det = upload_report_pdf_to_slack(
                settings=settings,
                pdf_bytes=pdf_bytes,
                filename=f"insight-report-{run_id}.pdf",
                initial_comment=(
                    f"Weekly insight report (PDF) for run `{run_id}` — same content as "
                    "report.html."
                ),
                logger=_log,
                timeout_seconds=settings.slack_pdf_upload_timeout_seconds,
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
            "report_docx_relative_path": docx_rel,
            "report_docx_byte_size": docx_size,
            "report_pdf_relative_path": pdf_rel,
            "report_pdf_byte_size": pdf_size,
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
        therapeutic_areas=_therapeutic_areas_for_slack(artifact_root, run_id, settings),
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
        report_pdf_relative_path=pdf_rel,
        report_pdf_byte_size=pdf_size,
        report_docx_relative_path=docx_rel,
        report_docx_byte_size=docx_size,
        distribution_channel=d_ch,
        distribution_status=d_st,
        distribution_detail=d_det,
        slack_notify_status=slack_st,
        slack_notify_detail=slack_det,
        slack_pdf_upload_status=pdf_st,
        slack_pdf_upload_detail=pdf_det,
        slack_docx_upload_status=docx_st,
        slack_docx_upload_detail=docx_det,
    )
