"""Slack Block Kit insight notifications (Epic 7)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pharma_rd.config import Settings, get_settings
from pharma_rd.integrations.slack_insight_notification import (
    build_slack_insight_blocks,
    format_report_location_for_notification,
    send_slack_insight_notification,
)
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.pipeline.contracts import (
    DomainCoverage,
    RankedOpportunityItem,
    SynthesisOutput,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_format_report_location_filesystem_vs_base_url(tmp_path: Path) -> None:
    rid = "run-x"
    root = tmp_path / "artifacts"
    root.mkdir()
    p = format_report_location_for_notification(root, rid, base_url=None)
    assert p == f"{rid}/delivery/report.docx"

    u = format_report_location_for_notification(
        root, rid, base_url="https://reports.example.com/reports"
    )
    assert u == "https://reports.example.com/reports/run-x/delivery/report.docx"

    h = format_report_location_for_notification(
        root, rid, base_url=None, report_basename="report.html"
    )
    assert h == f"{rid}/delivery/report.html"


def test_format_report_location_rejects_bad_basename(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    with pytest.raises(ValueError, match="report_basename"):
        format_report_location_for_notification(
            root, "run-x", base_url=None, report_basename="report.exe"
        )


def test_format_report_location_rejects_escape_attempts(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    with pytest.raises(ValueError, match="invalid run_id|escapes"):
        format_report_location_for_notification(root, "..", base_url=None)
    with pytest.raises(ValueError, match="invalid run_id|escapes"):
        format_report_location_for_notification(root, "a/../b", base_url=None)


def test_build_slack_blocks_escapes_mrkdwn_in_user_fields() -> None:
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r1",
        signal_characterization="quiet",
        ranked_opportunities=[
            RankedOpportunityItem(
                rank=1,
                title='Alpha *fake bold* & <tag>',
                rationale_short="Why _italic_?",
                domain_coverage=DomainCoverage(
                    clinical=True, competitor=False, consumer=False
                ),
                commercial_viability="`code`",
            ),
        ],
    )
    blocks, _ = build_slack_insight_blocks(
        run_id="run`id",
        run_date_utc=date(2026, 1, 1),
        synthesis=syn,
        settings=Settings(),
        artifact_root=Path("/tmp"),
    )
    dumped = str(blocks)
    assert "\\*" in dumped or "&amp;" in dumped
    assert "fake bold" in dumped


def test_build_slack_blocks_tied_rank_sorts_by_title() -> None:
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r1",
        signal_characterization="quiet",
        ranked_opportunities=[
            RankedOpportunityItem(
                rank=1,
                title="Zebra",
                rationale_short="z",
                domain_coverage=DomainCoverage(
                    clinical=True, competitor=False, consumer=False
                ),
                commercial_viability="",
            ),
            RankedOpportunityItem(
                rank=1,
                title="Alpha",
                rationale_short="a",
                domain_coverage=DomainCoverage(
                    clinical=True, competitor=False, consumer=False
                ),
                commercial_viability="",
            ),
        ],
    )
    blocks, _ = build_slack_insight_blocks(
        run_id="r",
        run_date_utc=date(2026, 1, 1),
        synthesis=syn,
        settings=Settings(),
        artifact_root=Path("/tmp"),
    )
    text = str(blocks)
    pos_alpha = text.find("Alpha")
    pos_zebra = text.find("Zebra")
    assert pos_alpha != -1 and pos_zebra != -1
    assert pos_alpha < pos_zebra


def test_build_slack_rationale_truncates_on_sentence_boundary() -> None:
    """Long rationale should not end mid-sentence when a sentence fits in the cap."""
    first = "A" * 38 + ". "
    rest = "B" * 400
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r1",
        signal_characterization="quiet",
        ranked_opportunities=[
            RankedOpportunityItem(
                rank=1,
                title="Op",
                rationale_short=first + rest,
                domain_coverage=DomainCoverage(
                    clinical=True, competitor=False, consumer=False
                ),
                commercial_viability="C" * 500,
            ),
        ],
    )
    blocks, _ = build_slack_insight_blocks(
        run_id="r1",
        run_date_utc=date(2026, 1, 1),
        synthesis=syn,
        settings=Settings(),
        artifact_root=Path("/tmp"),
    )
    dumped = str(blocks)
    assert "Why it matters:" in dumped
    assert "…" in dumped
    assert "B" * 20 not in dumped
    assert (first.rstrip() + "…") in dumped or first.rstrip() in dumped


def test_build_slack_blocks_no_fr22_or_governance_in_slack_message() -> None:
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r1",
        signal_characterization="quiet",
        ranked_opportunities=[],
    )
    blocks, text_fb = build_slack_insight_blocks(
        run_id="r1",
        run_date_utc=date(2026, 1, 1),
        synthesis=syn,
        settings=Settings(),
        artifact_root=Path("/tmp"),
    )
    combined = str(blocks) + text_fb
    assert "(FR22)" not in combined
    assert "Human judgment" not in combined
    assert "human-owned" not in combined.lower()


def test_build_slack_blocks_contains_ac_content() -> None:
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r1",
        signal_characterization="net_new",
        ranked_opportunities=[
            RankedOpportunityItem(
                rank=1,
                title="Op A",
                rationale_short="Because markets.",
                domain_coverage=DomainCoverage(
                    clinical=True, competitor=False, consumer=False
                ),
                commercial_viability="Strong fit.",
            ),
            RankedOpportunityItem(
                rank=2,
                title="Op B",
                rationale_short="Second.",
                domain_coverage=DomainCoverage(
                    clinical=False, competitor=True, consumer=False
                ),
                commercial_viability="Moderate.",
            ),
        ],
    )
    settings = Settings(
        therapeutic_areas="Oncology, Rare",
        competitor_watchlist="Acme, BetaBio",
    )
    blocks, text_fb = build_slack_insight_blocks(
        run_id="run-z",
        run_date_utc=date(2026, 4, 5),
        synthesis=syn,
        settings=settings,
        artifact_root=Path("/tmp/art"),
    )
    assert blocks
    dumped = str(blocks) + text_fb
    assert "Weekly research brief" in dumped
    assert "strong week" in dumped or "stood out" in dumped
    assert "Op A" in dumped
    assert "Oncology" in dumped
    assert "Acme" in dumped
    assert "What I monitored" in dumped
    assert "report.docx" in dumped
    assert "report.html" in dumped


def test_build_slack_blocks_therapeutic_areas_override_from_run() -> None:
    """Clinical artifact scope can be passed explicitly (matches monitored TAs)."""
    syn = SynthesisOutput(
        schema_version=5,
        run_id="r1",
        signal_characterization="quiet",
        ranked_opportunities=[],
    )
    blocks, _ = build_slack_insight_blocks(
        run_id="r1",
        run_date_utc=date(2026, 1, 1),
        synthesis=syn,
        settings=Settings(),
        artifact_root=Path("/tmp"),
        therapeutic_areas=["Dermatology", "Immunology"],
    )
    dumped = str(blocks)
    assert "Dermatology" in dumped
    assert "Immunology" in dumped
    assert "No therapeutic-area list" not in dumped


def test_send_slack_skipped_no_post_no_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.INFO)
    get_settings.cache_clear()
    syn = SynthesisOutput(run_id="a", signal_characterization="quiet")
    st, det = send_slack_insight_notification(
        webhook_url=get_settings().slack_webhook_url,
        run_id="a",
        synthesis=syn,
        settings=get_settings(),
        artifact_root=Path("."),
        logger=get_pipeline_logger("test.slack"),
        timeout_seconds=10.0,
    )
    assert st == "skipped"
    assert det == ""
    skipped = any(
        getattr(r, "event", None) == "slack_notify_skipped" for r in caplog.records
    )
    assert skipped


def test_send_slack_posts_httpx_json_with_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog
) -> None:
    import logging

    caplog.set_level(logging.INFO)
    monkeypatch.setenv(
        "PHARMA_RD_SLACK_WEBHOOK_URL",
        "https://hooks.slack.com/services/T00/B00/XXXXXXXX",
    )
    get_settings.cache_clear()
    settings = get_settings()
    syn = SynthesisOutput(
        schema_version=5,
        run_id="slack-run",
        signal_characterization="quiet",
        ranked_opportunities=[],
    )
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_client
    mock_cm.__exit__.return_value = None

    with patch(
        "pharma_rd.integrations.slack_insight_notification.httpx.Client",
        return_value=mock_cm,
    ):
        st, det = send_slack_insight_notification(
            webhook_url=settings.slack_webhook_url,
            run_id="slack-run",
            synthesis=syn,
            settings=settings,
            artifact_root=tmp_path,
            logger=get_pipeline_logger("test.slack"),
            timeout_seconds=10.0,
        )

    assert st == "ok"
    assert "200" in det
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0].startswith("https://hooks.slack.com/")
    body = kwargs["json"]
    assert "blocks" in body
    assert isinstance(body["blocks"], list)
    assert "text" in body
    dumped = str(body["blocks"]) + body["text"]
    assert "Weekly research brief" in dumped
    assert "At a glance" in dumped or "quieter week" in dumped
    complete = any(
        getattr(r, "event", None) == "slack_notify_complete" for r in caplog.records
    )
    assert complete


def test_send_slack_http_error_does_not_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_SLACK_WEBHOOK_URL",
        "https://hooks.slack.com/services/T00/B00/XXXXXXXX",
    )
    get_settings.cache_clear()
    settings = get_settings()
    syn = SynthesisOutput(run_id="x", signal_characterization="unknown")
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 500
    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_client
    mock_cm.__exit__.return_value = None
    with patch(
        "pharma_rd.integrations.slack_insight_notification.httpx.Client",
        return_value=mock_cm,
    ):
        st, det = send_slack_insight_notification(
            webhook_url=settings.slack_webhook_url,
            run_id="x",
            synthesis=syn,
            settings=settings,
            artifact_root=tmp_path,
            logger=get_pipeline_logger("test.slack"),
            timeout_seconds=10.0,
        )
    assert st == "failed"
    assert "500" in det
