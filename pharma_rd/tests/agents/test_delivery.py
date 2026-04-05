"""Delivery agent — FR18."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from pharma_rd.agents.delivery import run_delivery
from pharma_rd.config import get_settings
from pharma_rd.pipeline.contracts import (
    DomainCoverage,
    EvidenceReferenceItem,
    RankedOpportunityItem,
    SynthesisOutput,
)
from pharma_rd.readability import validate_readable_insight_report


def test_run_delivery_writes_report_and_output_metadata(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    rid = "run-7-1"
    syn = SynthesisOutput(
        schema_version=5,
        run_id=rid,
        signal_characterization="net_new",
        scan_summary_lines=["Clinical: pubs=1 internal=0 tas=none"],
        ranked_opportunities=[
            RankedOpportunityItem(
                rank=1,
                title="Clinical: Alpha · Competitor: (no item)",
                rationale_short="Clinical “Alpha”: more text here.",
                domain_coverage=DomainCoverage(
                    clinical=True,
                    competitor=False,
                    consumer=False,
                ),
                evidence_references=[
                    EvidenceReferenceItem(
                        domain="clinical",
                        label="Alpha",
                        reference="pmid:99",
                    )
                ],
                commercial_viability="Clinical: cited evidence.",
            )
        ],
    )
    root = tmp_path / "art"
    root.mkdir()
    out = run_delivery(rid, syn, root)
    assert out.schema_version == 3
    assert out.report_format == "markdown"
    assert out.report_byte_size > 0
    assert out.report_relative_path == f"{rid}/delivery/report.md"
    assert out.report_html_relative_path == f"{rid}/delivery/report.html"
    assert out.report_html_byte_size > 0
    assert out.distribution_channel == "none"
    assert out.distribution_status == "skipped"
    assert out.distribution_detail
    assert out.slack_notify_status == "skipped"
    assert out.slack_notify_detail == ""
    assert any(
        getattr(r, "event", None) == "slack_notify_skipped" for r in caplog.records
    )
    report_path = root / rid / "delivery" / "report.md"
    report = report_path.read_text(encoding="utf-8")
    assert rid in report
    assert "net_new" in report
    assert "Clinical: pubs=1" in report
    assert "Alpha" in report
    assert "pmid:99" in report
    assert "Governance and disclaimer" in report
    assert "Human judgment (FR22)" in report
    assert "Deployment (FR26)" in report
    assert "enterprise sso" in report.lower()
    assert "recommendation" in report.lower()
    assert "human-owned" in report.lower()
    assert "pursuit" in report.lower()
    assert "Recommendation only—not an approval" in report
    validate_readable_insight_report(
        report_path,
        required_content_snippets=(
            "Clinical: Alpha · Competitor: (no item)",
            "pmid:99",
        ),
    )
    html = (root / rid / "delivery" / "report.html").read_text(encoding="utf-8")
    assert "<h2>Run summary</h2>" in html
    assert "<h2>Ranked opportunities</h2>" in html
    assert "<h2>Governance and disclaimer</h2>" in html
    assert "<footer>" in html
    assert "Human judgment (FR22)" in html
    assert "Deployment (FR26)" in html
    assert "enterprise sso" in html.lower()
    assert "human-owned" in html.lower()
    assert "Recommendation only—not an approval" in html
    assert "Clinical: Alpha" in html


def test_run_summary_skips_fr26_banner_when_not_practice_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PHARMA_RD_DEPLOYMENT_PROFILE", "staging")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    try:
        rid = "run-8-4-staging"
        syn = SynthesisOutput(
            schema_version=5,
            run_id=rid,
            signal_characterization="quiet",
            scan_summary_lines=[],
            ranked_opportunities=[],
        )
        root = tmp_path / "art"
        root.mkdir()
        run_delivery(rid, syn, root)
        report = (root / rid / "delivery" / "report.md").read_text(encoding="utf-8")
        assert "Deployment (FR26)" not in report
        html = (root / rid / "delivery" / "report.html").read_text(encoding="utf-8")
        assert "Deployment (FR26)" not in html
        validate_readable_insight_report(
            root / rid / "delivery" / "report.md",
            required_content_snippets=("quiet",),
        )
    finally:
        get_settings.cache_clear()


def test_run_delivery_file_drop_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pharma_rd.config import get_settings

    rid = "run-7-2-drop"
    syn = SynthesisOutput(
        schema_version=5,
        run_id=rid,
        signal_characterization="quiet",
        scan_summary_lines=["a"],
        ranked_opportunities=[],
    )
    root = tmp_path / "art"
    root.mkdir()
    drop = tmp_path / "drop"
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "file_drop")
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_DROP_DIR", str(drop))
    get_settings.cache_clear()
    try:
        out = run_delivery(rid, syn, root)
    finally:
        get_settings.cache_clear()
    assert out.schema_version == 3
    assert out.distribution_channel == "file_drop"
    assert out.distribution_status == "ok"
    canonical = root / rid / "delivery" / "report.md"
    rd_md = drop / "rd" / rid / "report.md"
    mk_md = drop / "marketing" / rid / "report.md"
    assert rd_md.is_file()
    assert mk_md.is_file()
    blob = canonical.read_bytes()
    assert rd_md.read_bytes() == blob
    assert mk_md.read_bytes() == blob
    validate_readable_insight_report(rd_md, required_content_snippets=("quiet",))
    validate_readable_insight_report(mk_md, required_content_snippets=("quiet",))
    rd_html = drop / "rd" / rid / "report.html"
    canon_html = root / rid / "delivery" / "report.html"
    assert rd_html.read_bytes() == canon_html.read_bytes()
    assert out.slack_notify_status == "skipped"


def test_run_delivery_slack_webhook_configured_posts_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_SLACK_WEBHOOK_URL",
        "https://hooks.slack.com/services/T00/B00/XXXXXXXX",
    )
    get_settings.cache_clear()
    try:
        rid = "run-7-slack"
        syn = SynthesisOutput(
            schema_version=5,
            run_id=rid,
            signal_characterization="mixed",
            scan_summary_lines=["s"],
            ranked_opportunities=[
                RankedOpportunityItem(
                    rank=1,
                    title="First",
                    rationale_short="Rationale text for Slack.",
                    domain_coverage=DomainCoverage(
                        clinical=True,
                        competitor=False,
                        consumer=True,
                    ),
                    commercial_viability="Viability note.",
                )
            ],
        )
        root = tmp_path / "art"
        root.mkdir()
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
            out = run_delivery(rid, syn, root)
        assert out.slack_notify_status == "ok"
        assert "200" in out.slack_notify_detail
        args, kwargs = mock_client.post.call_args
        body = kwargs["json"]
        assert "blocks" in body
        joined = str(body["blocks"]) + body.get("text", "")
        assert "pharma_RD" in joined
        assert "recommendations" in joined.lower()
        assert "First" in joined
    finally:
        get_settings.cache_clear()


def test_run_delivery_run_id_mismatch() -> None:
    with pytest.raises(ValueError, match="run_id mismatch"):
        run_delivery(
            "a",
            SynthesisOutput(run_id="b"),
            Path("."),
        )


def _gpt_json_ok() -> str:
    return json.dumps(
        {
            "report_html": (
                "<section><h1>Insight report</h1>"
                "<p>Human judgment (FR22): Items in this report are recommendations "
                "for review only—not approvals. Pursuit and portfolio decisions "
                "remain human-owned.</p>"
                "<p>Recommendation only—not an approval. "
                "Pursuit is a human decision.</p>"
                "<p>Commercial conclusion: validate externally.</p></section>"
            ),
            "report_markdown": (
                "# Insight\n\n"
                "Human judgment (FR22): Items in this report are recommendations "
                "for review only—not approvals.\n\n"
                "Recommendation only—not an approval.\n"
            ),
            "slack_executive_excerpt": "Strategic week: review ranked opportunities.",
        }
    )


def test_run_delivery_gpt_renderer_mocked_openai(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PHARMA_RD_REPORT_RENDERER", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    try:
        rid = "run-gpt"
        syn = SynthesisOutput(
            schema_version=5,
            run_id=rid,
            signal_characterization="net_new",
            scan_summary_lines=["Clinical: pubs=1"],
            ranked_opportunities=[],
        )
        root = tmp_path / "art"
        root.mkdir()
        with patch(
            "pharma_rd.integrations.openai_report_delivery.run_chat_json_completion",
            return_value=(_gpt_json_ok(), None),
        ):
            run_delivery(rid, syn, root)
        md = (root / rid / "delivery" / "report.md").read_text(encoding="utf-8")
        html = (root / rid / "delivery" / "report.html").read_text(encoding="utf-8")
        assert "Human judgment (FR22)" in md
        assert "<!DOCTYPE html>" in html
        assert "Human judgment (FR22)" in html
        assert "<script>" not in html.lower()
    finally:
        get_settings.cache_clear()


def test_run_delivery_gpt_thin_output_falls_back_to_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("PHARMA_RD_REPORT_RENDERER", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    try:
        rid = "run-thin"
        syn = SynthesisOutput(
            schema_version=5,
            run_id=rid,
            signal_characterization="quiet",
            scan_summary_lines=[],
            ranked_opportunities=[],
        )
        root = tmp_path / "art"
        root.mkdir()
        thin = json.dumps(
            {
                "report_html": "<p>x</p>",
                "report_markdown": "y",
            }
        )
        with patch(
            "pharma_rd.integrations.openai_report_delivery.run_chat_json_completion",
            return_value=(thin, None),
        ):
            run_delivery(rid, syn, root)
        md = (root / rid / "delivery" / "report.md").read_text(encoding="utf-8")
        assert "Human judgment (FR22)" in md
        assert "Insight report" in md
        assert any(
            getattr(r, "event", None) == "delivery_gpt_fallback" for r in caplog.records
        )
    finally:
        get_settings.cache_clear()


def test_run_delivery_gpt_fallback_to_template_on_api_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("PHARMA_RD_REPORT_RENDERER", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    try:
        rid = "run-fb"
        syn = SynthesisOutput(
            schema_version=5,
            run_id=rid,
            signal_characterization="quiet",
            scan_summary_lines=[],
            ranked_opportunities=[],
        )
        root = tmp_path / "art"
        root.mkdir()
        with patch(
            "pharma_rd.integrations.openai_report_delivery.run_chat_json_completion",
            return_value=(None, "RateLimitError: 429"),
        ):
            run_delivery(rid, syn, root)
        md = (root / rid / "delivery" / "report.md").read_text(encoding="utf-8")
        assert "Human judgment (FR22)" in md
        assert "Insight report" in md
        assert any(
            getattr(r, "event", None) == "delivery_gpt_fallback" for r in caplog.records
        )
    finally:
        get_settings.cache_clear()


def test_run_delivery_gpt_failure_without_fallback_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PHARMA_RD_REPORT_RENDERER", "gpt")
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("PHARMA_RD_REPORT_GPT_FALLBACK_ON_ERROR", "false")
    get_settings.cache_clear()
    try:
        rid = "run-err"
        syn = SynthesisOutput(
            schema_version=5,
            run_id=rid,
            signal_characterization="quiet",
            ranked_opportunities=[],
        )
        root = tmp_path / "art"
        root.mkdir()
        with patch(
            "pharma_rd.integrations.openai_report_delivery.run_chat_json_completion",
            return_value=(None, "APIStatusError"),
        ):
            with pytest.raises(ValueError, match="GPT report delivery failed"):
                run_delivery(rid, syn, root)
    finally:
        get_settings.cache_clear()
