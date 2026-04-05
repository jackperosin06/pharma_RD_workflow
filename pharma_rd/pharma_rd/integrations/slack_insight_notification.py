"""Slack Block Kit notifications after insight report delivery (Epic 7 / FR19).

Uses ``httpx`` POST to an incoming webhook URL. Block assembly stays here; Delivery
orchestrates only. Does not import ``pharma_rd.agents.delivery`` (avoid cycles).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

from pharma_rd.config import Settings

if TYPE_CHECKING:
    from pharma_rd.pipeline.contracts import SlackNotifyStatus, SynthesisOutput

# Mirror FR22 tone from ``delivery.py`` (single legal meaning; Slack-sized).
_FR22_SLACK = (
    "Items in this report are *recommendations* for review only—not *approvals*. "
    "*Pursuit and portfolio decisions remain human-owned* (FR22)."
)

# Slack ``section`` mrkdwn practical caps (Block Kit allows 3000; stay smaller).
_CAP_RATIONALE = 220
_CAP_COMMERCIAL = 140
_CAP_FALLBACK_TEXT = 3500


def format_report_location_for_notification(
    artifact_root: Path,
    run_id: str,
    *,
    base_url: str | None = None,
) -> str:
    """Where to open the HTML report: filesystem path (MVP) or future HTTPS URL.

    When ``base_url`` is set (e.g. ``https://reports.example.com``), returns a URL
    path under that base without changing Block Kit assembly elsewhere.
    """
    rel = f"{run_id}/delivery/report.html"
    if base_url is not None:
        b = base_url.strip().rstrip("/")
        return f"{b}/{rel}"
    root = artifact_root.expanduser().resolve()
    rel_path = Path(run_id) / "delivery" / "report.html"
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


def _signal_summary_md(sig: str) -> str:
    if sig == "quiet":
        return (
            "Executive view: this run looks like a *quiet week*—limited new "
            "cross-domain signal versus a high-activity week. Open the full report "
            "for nuance."
        )
    if sig == "net_new":
        return (
            "Executive view: *high-signal week*—characterization *net_new* suggests "
            "notable new threads worth review."
        )
    if sig == "mixed":
        return (
            "Executive view: *mixed* signal week—some domains may be quiet while "
            "others show activity; see ranked items below."
        )
    return (
        "Executive view: characterization *unknown*—use the full HTML report for "
        "complete context."
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
) -> tuple[list[dict[str, Any]], str]:
    """Return Block Kit ``blocks`` and a plain ``text`` fallback for Slack clients."""

    blocks: list[dict[str, Any]] = []

    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "pharma_RD insight report",
                "emoji": True,
            },
        }
    )
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Run date (UTC):* {run_date_utc.isoformat()}\n"
                f"*Run ID:* `{_escape_slack_mrkdwn_user_text(run_id)}`",
            },
        }
    )
    blocks.append({"type": "divider"})
    if gpt_executive_excerpt and gpt_executive_excerpt.strip():
        exc = _truncate_at_word(gpt_executive_excerpt.strip(), 900)
        exec_md = "*Executive summary*\n" + _escape_slack_mrkdwn_user_text(exc)
    else:
        exec_md = "*Executive summary*\n" + _signal_summary_md(
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
    opp_lines: list[str] = ["*Top opportunities (by rank)*"]
    if not ranked:
        opp_lines.append("_No ranked opportunities in this run._")
    else:
        for row in ranked:
            rat = _escape_slack_mrkdwn_user_text(
                _truncate_at_word(row.rationale_short, _CAP_RATIONALE)
            )
            comm = _escape_slack_mrkdwn_user_text(
                _truncate_at_word(row.commercial_viability or "—", _CAP_COMMERCIAL)
            )
            title_safe = _escape_slack_mrkdwn_user_text(row.title)
            opp_lines.append(
                f"*{row.rank}.* {title_safe}\n"
                f"Rationale: {rat}\n"
                f"Commercial viability: {comm}"
            )
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n\n".join(opp_lines)},
        }
    )
    blocks.append({"type": "divider"})

    tas = settings.therapeutic_area_labels()
    comps = settings.competitor_labels()
    ta_part = (
        ", ".join(f"*{_escape_slack_mrkdwn_user_text(t)}*" for t in tas)
        if tas
        else "*not configured* / none"
    )
    co_part = (
        ", ".join(f"*{_escape_slack_mrkdwn_user_text(c)}*" for c in comps)
        if comps
        else "*not configured* / none"
    )
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Scan / monitoring summary*\n"
                    f"• Therapeutic areas: {ta_part}\n"
                    f"• Competitor watchlists: {co_part}"
                ),
            },
        }
    )
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Human judgment (FR22)*\n" + _FR22_SLACK,
            },
        }
    )
    blocks.append({"type": "divider"})
    loc = format_report_location_for_notification(artifact_root, run_id, base_url=None)
    loc_safe = _escape_slack_mrkdwn_user_text(loc)
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Full HTML report:*\n`{loc_safe}`",
            },
        }
    )

    fallback = (
        f"pharma_RD insight report — {run_date_utc.isoformat()} UTC — run {run_id}. "
        f"Open HTML: {loc}"
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
