"""Slack Web API PDF upload."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from pharma_rd.config import Settings, get_settings
from pharma_rd.integrations.slack_pdf_upload import upload_report_pdf_to_slack
from pharma_rd.logging_setup import get_pipeline_logger


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_upload_pdf_skipped_without_token_or_channel() -> None:
    st, det = upload_report_pdf_to_slack(
        settings=Settings(),
        pdf_bytes=b"%PDF",
        filename="x.pdf",
        initial_comment="hi",
        logger=get_pipeline_logger("test.slack.pdf"),
        timeout_seconds=10.0,
    )
    assert st == "skipped"
    assert det == ""


def test_upload_pdf_ok_three_step_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("PHARMA_RD_SLACK_PDF_CHANNEL_ID", "C01234567")
    get_settings.cache_clear()
    settings = get_settings()

    mock_get = MagicMock(spec=httpx.Response)
    mock_get.status_code = 200
    mock_get.json.return_value = {
        "ok": True,
        "upload_url": "https://files.upload.example/upload/1",
        "file_id": "F12345",
    }
    mock_put = MagicMock(spec=httpx.Response)
    mock_put.status_code = 200
    mock_complete = MagicMock(spec=httpx.Response)
    mock_complete.status_code = 200
    mock_complete.json.return_value = {"ok": True}

    mock_client = MagicMock()
    mock_client.post.side_effect = [mock_get, mock_complete]
    mock_client.put.return_value = mock_put
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_client
    mock_cm.__exit__.return_value = None

    with patch(
        "pharma_rd.integrations.slack_pdf_upload.httpx.Client",
        return_value=mock_cm,
    ):
        st, det = upload_report_pdf_to_slack(
            settings=settings,
            pdf_bytes=b"%PDF-1.4 test",
            filename="insight-report-run.pdf",
            initial_comment="Weekly PDF",
            logger=get_pipeline_logger("test.slack.pdf"),
            timeout_seconds=30.0,
        )

    assert st == "ok"
    assert "ok" in det.lower()
    assert mock_client.post.call_count == 2
    mock_client.put.assert_called_once()
