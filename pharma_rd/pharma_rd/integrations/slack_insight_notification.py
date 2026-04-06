"""Slack Block Kit notifications after insight report delivery (Epic 7 / FR19).

Uses ``httpx`` POST to an incoming webhook URL. Block assembly stays here; Delivery
orchestrates only. Does not import ``pharma_rd.agents.delivery`` (avoid cycles).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

from pharma_rd.config import Settings

if TYPE_CHECKING:
    from pharma_rd.pipeline.contracts import SlackNotifyStatus, SynthesisOutput

# Slack ``section`` mrkdwn practical caps (Block Kit allows 3000; stay smaller).
_CAP_RATIONALE = 220
_CAP_COMMERCIAL = 140
_CAP_FALLBACK_TEXT = 3500

_ALLOWED_REPORT_BASENAMES = frozenset(
    {"report.docx", "report.html", "report.md", "report.pdf"}
)


def format_report_location_for_notification(
    artifact_root: Path,
    run_id: str,
    *,
    base_url: str | None = None,
    report_basename: str = "report.docx",
) -> str:
    """Filesystem-relative path or HTTPS URL to a report file under ``delivery/``.

    Default ``report_basename`` is ``report.docx`` so Slack points at the Word
    artifact. Use ``report.html`` for browser, etc.

    When ``base_url`` is set (e.g. ``https://reports.example.com``), returns a URL
    path under that base without changing Block Kit assembly elsewhere.
    """
    if report_basename not in _ALLOWED_REPORT_BASENAMES:
        raise ValueError(
            f"report_basename must be one of {_ALLOWED_REPORT_BASENAMES}; "
            f"got {report_basename!r}"
        )
    rel = f"{run_id}/delivery/{report_basename}"
    if base_url is not None:
        b = base_url.strip().rstrip("/")
        return f"{b}/{rel}"
    root = artifact_root.expanduser().resolve()
    rel_path = Path(run_id) / "delivery" / report_basename
    if rel_path.is_absolute() or any(p == ".." for p in Path(run_id).parts):
        raise ValueError(f"invalid run_id: {run_id!r}")
    resolved = (root / rel_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as e:
        raise ValueError(f"run_id escapes artifact root: {run_id!r}") from e
    return rel


def _truncate_at_word(text: str, max_len: int) -> str:
    t = text.strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


# Sentence-ending punctuation followed by whitespace or end of truncated prefix.
_SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def _truncate_at_sentence_boundary(text: str, max_len: int) -> str:
    """Shorten text to ``max_len``, preferring the last *complete* sentence in range."""
    t = " ".join(text.split())
    if len(t) <= max_len:
        return t
    ellipsis = "…"
    budget = max_len - len(ellipsis)
    if budget <= 0:
        return ellipsis[:max_len]
    prefix = t[:budget]
    last_end = 0
    for m in _SENTENCE_END.finditer(prefix):
        last_end = m.end()
    if last_end > 0:
        return t[:last_end].rstrip() + ellipsis
    return _truncate_at_word(t, max_len)


def _escape_slack_mrkdwn_user_text(text: str) -> str:
    """Escape user/config strings embedded in Slack mrkdwn section text."""
    t = text.replace("\\", "\\\\")
    t = t.replace("&", "&amp;")
    t = t.replace("<", "&lt;")
    t = t.replace(">", "&gt;")
    t = t.replace("*", "\\*")
    t = t.replace("_", "\\_")
    t = t.replace("~", "\\~")
    t = t.replace("`", "\\`")
    return t


def _format_brief_date_utc(d: date) -> str:
    """Readable calendar line, e.g. ``April 6, 2026`` (no zero-padded day)."""
    return f"{d:%B} {d.day}, {d.year}"


def _signal_summary_md(sig: str) -> str:
    if sig == "quiet":
        return (
            "Overall this looks like a *quieter week*—lighter cross-domain signal "
            "than a busy stretch. I still pulled the highlights below; the full "
            "report has the detail."
        )
    if sig == "net_new":
        return (
            "This was a *strong week* for new threads—several items tie together "
            "across domains, so they are worth a careful read."
        )
    if sig == "mixed":
        return (
            "Signal was *mixed* this week—some areas were quiet while others moved. "
            "The ranked list below is where I focused your attention."
        )
    return (
        "I could not classify the week cleanly from the snapshot alone—use the "
        "full report for the complete picture."
    )


def _webhook_host_for_log(url: str) -> str:
    host = urlparse(url).hostname
    return host if host else "unknown"


def build_slack_insight_blocks(
    *,
    run_id: str,
    run_date_utc: date,
    synthesis: SynthesisOutput,
    settings: Settings,
    artifact_root: Path,
    gpt_executive_excerpt: str | None = None,
    therapeutic_areas: list[str] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Return Block Kit ``blocks`` and a plain ``text`` fallback for Slack clients."""

    blocks: list[dict[str, Any]] = []
    org = (settings.insight_org_display_name or "").strip() or "your organization"
    brief_when = _format_brief_date_utc(run_date_utc)
    tas_src = (
        therapeutic_areas
        if therapeutic_areas is not None
        else settings.therapeutic_area_labels()
    )

    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Weekly research brief — {org}",
                "emoji": True,
            },
        }
    )
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Week of* {brief_when} (UTC)\n"
                    "Here is a short recap of what I reviewed in the monitoring pass—"
                    "citations and depth are in the full report.\n"
                    f"Reference: `{_escape_slack_mrkdwn_user_text(run_id)}`"
                ),
            },
        }
    )
    blocks.append({"type": "divider"})
    if gpt_executive_excerpt and gpt_executive_excerpt.strip():
        exc = _truncate_at_sentence_boundary(gpt_executive_excerpt.strip(), 900)
        exec_md = "*At a glance*\n" + _escape_slack_mrkdwn_user_text(exc)
    else:
        exec_md = "*At a glance*\n" + _signal_summary_md(
            synthesis.signal_characterization
        )
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": exec_md,
            },
        }
    )
    blocks.append({"type": "divider"})

    ranked = sorted(
        synthesis.ranked_opportunities,
        key=lambda r: (r.rank, r.title),
    )[:3]
    opp_lines: list[str] = ["*What stood out*"]
    if not ranked:
        opp_lines.append("_Nothing was ranked this week—see the report for gaps._")
    else:
        for row in ranked:
            rat = _escape_slack_mrkdwn_user_text(
                _truncate_at_sentence_boundary(row.rationale_short, _CAP_RATIONALE)
            )
            comm = _escape_slack_mrkdwn_user_text(
                _truncate_at_sentence_boundary(
                    row.commercial_viability or "—", _CAP_COMMERCIAL
                )
            )
            title_safe = _escape_slack_mrkdwn_user_text(row.title)
            opp_lines.append(
                f"*{row.rank}.* {title_safe}\n"
                f"Why it matters: {rat}\n"
                f"Commercial angle: {comm}"
            )
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n\n".join(opp_lines)},
        }
    )
    blocks.append({"type": "divider"})

    comps = settings.competitor_labels()
    ta_part = (
        ", ".join(f"*{_escape_slack_mrkdwn_user_text(t)}*" for t in tas_src)
        if tas_src
        else "_No therapeutic-area list was applied to the clinical scan this run._"
    )
    co_part = (
        ", ".join(f"*{_escape_slack_mrkdwn_user_text(c)}*" for c in comps)
        if comps
        else "_No competitor names on the watchlist for this run._"
    )
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*What I monitored*\n"
                    f"• Therapeutic areas covered: {ta_part}\n"
                    f"• Competitors on watch: {co_part}"
                ),
            },
        }
    )
    blocks.append({"type": "divider"})
    loc_docx = format_report_location_for_notification(
        artifact_root, run_id, base_url=None, report_basename="report.docx"
    )
    loc_html = format_report_location_for_notification(
        artifact_root, run_id, base_url=None, report_basename="report.html"
    )
    docx_safe = _escape_slack_mrkdwn_user_text(loc_docx)
    html_safe = _escape_slack_mrkdwn_user_text(loc_html)
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Full report*\n"
                    f"• Word: `{docx_safe}`\n"
                    f"• HTML (browser): `{html_safe}`"
                ),
            },
        }
    )

    fallback = (
        f"Weekly research brief — {org} — week of {brief_when} UTC — run {run_id}. "
        f"Word: {loc_docx} — HTML: {loc_html}"
    )
    if len(fallback) > _CAP_FALLBACK_TEXT:
        fallback = fallback[: _CAP_FALLBACK_TEXT - 1] + "…"
    return blocks, fallback


def send_slack_insight_notification(
    *,
    webhook_url: str | None,
    run_id: str,
    synthesis: SynthesisOutput,
    settings: Settings,
    artifact_root: Path,
    logger: logging.Logger,
    timeout_seconds: float,
    gpt_executive_excerpt: str | None = None,
    therapeutic_areas: list[str] | None = None,
) -> tuple[SlackNotifyStatus, str]:
    """POST Block Kit payload to Slack, or skip with structured INFO log."""

    if not webhook_url:
        logger.info(
            "slack notify skipped",
            extra={
                "event": "slack_notify_skipped",
                "outcome": "skipped",
                "slack_notify_status": "skipped",
                "slack_webhook_configured": False,
            },
        )
        return "skipped", ""

    run_date_utc = datetime.now(UTC).date()
    blocks, text_fb = build_slack_insight_blocks(
        run_id=run_id,
        run_date_utc=run_date_utc,
        synthesis=synthesis,
        settings=settings,
        artifact_root=artifact_root,
        gpt_executive_excerpt=gpt_executive_excerpt,
        therapeutic_areas=therapeutic_areas,
    )
    payload: dict[str, Any] = {"text": text_fb, "blocks": blocks}
    host = _webhook_host_for_log(webhook_url)

    try:
        timeout = httpx.Timeout(timeout_seconds)
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            resp = client.post(webhook_url, json=payload)
        if 200 <= resp.status_code < 300:
            logger.info(
                "slack notify complete",
                extra={
                    "event": "slack_notify_complete",
                    "outcome": "ok",
                    "slack_notify_status": "ok",
                    "slack_webhook_configured": True,
                    "slack_webhook_host": host,
                    "http_status": resp.status_code,
                },
            )
            return "ok", f"http_status={resp.status_code}"
        detail = f"http_status={resp.status_code}"
        logger.error(
            "slack notify failed",
            extra={
                "event": "slack_notify_failed",
                "outcome": "failed",
                "slack_notify_status": "failed",
                "slack_webhook_configured": True,
                "slack_webhook_host": host,
                "http_status": resp.status_code,
                "slack_notify_detail": detail[:300],
            },
        )
        return "failed", detail
    except httpx.TimeoutException:
        detail = "timeout"
        logger.error(
            "slack notify failed",
            extra={
                "event": "slack_notify_failed",
                "outcome": "failed",
                "slack_notify_status": "failed",
                "slack_webhook_configured": True,
                "slack_webhook_host": host,
                "error_type": "timeout",
                "slack_notify_detail": detail,
            },
        )
        return "failed", detail
    except httpx.RequestError as e:
        detail = "request_error"
        logger.error(
            "slack notify failed",
            extra={
                "event": "slack_notify_failed",
                "outcome": "failed",
                "slack_notify_status": "failed",
                "slack_webhook_configured": True,
                "slack_webhook_host": host,
                "error_type": type(e).__name__,
                "slack_notify_detail": detail,
            },
        )
        return "failed", detail
