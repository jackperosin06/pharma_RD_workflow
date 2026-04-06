"""Upload files to Slack via Web API (``files.getUploadURLExternal`` flow)."""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx

from pharma_rd.config import Settings

SlackPdfUploadStatus = Literal["ok", "skipped", "failed"]


def _slack_api_ok(data: dict[str, Any]) -> bool:
    return bool(data.get("ok"))


def upload_file_to_slack_channel(
    *,
    settings: Settings,
    file_bytes: bytes,
    filename: str,
    initial_comment: str,
    logger: logging.Logger,
    timeout_seconds: float,
) -> tuple[SlackPdfUploadStatus, str]:
    """Post ``file_bytes`` to ``settings.slack_pdf_channel_id`` using bot token.

    Works for PDF, Word, HTML, etc. Skips when bot token or channel id is unset.
    Does not raise on HTTP/API errors; returns ``failed`` and logs.
    """
    token = settings.slack_bot_token
    channel = settings.slack_pdf_channel_id
    if not token or not channel:
        logger.info(
            "slack file upload skipped",
            extra={
                "event": "slack_file_upload_skipped",
                "outcome": "skipped",
                "slack_file_upload_status": "skipped",
                "reason": "missing_bot_token_or_channel",
            },
        )
        return "skipped", ""

    host = "slack.com"
    try:
        timeout = httpx.Timeout(timeout_seconds)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r1 = client.post(
                "https://slack.com/api/files.getUploadURLExternal",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "filename": filename,
                    "length": str(len(file_bytes)),
                },
            )
            d1 = r1.json()
            if not _slack_api_ok(d1):
                detail = str(d1.get("error", "unknown"))[:200]
                logger.error(
                    "slack file upload failed",
                    extra={
                        "event": "slack_file_upload_failed",
                        "outcome": "failed",
                        "slack_file_upload_status": "failed",
                        "slack_api_step": "getUploadURLExternal",
                        "slack_notify_detail": detail,
                        "http_status": r1.status_code,
                    },
                )
                return "failed", detail

            upload_url = d1.get("upload_url")
            file_id = d1.get("file_id")
            if not isinstance(upload_url, str) or not isinstance(file_id, str):
                detail = "missing_upload_url_or_file_id"
                logger.error(
                    "slack file upload failed",
                    extra={
                        "event": "slack_file_upload_failed",
                        "outcome": "failed",
                        "slack_file_upload_status": "failed",
                        "slack_api_step": "getUploadURLExternal",
                        "slack_notify_detail": detail,
                    },
                )
                return "failed", detail

            put = client.put(
                upload_url,
                content=file_bytes,
                headers={"Content-Type": "application/octet-stream"},
            )
            if not (200 <= put.status_code < 300):
                detail = f"upload_put_http={put.status_code}"
                logger.error(
                    "slack file upload failed",
                    extra={
                        "event": "slack_file_upload_failed",
                        "outcome": "failed",
                        "slack_file_upload_status": "failed",
                        "slack_api_step": "put_upload_url",
                        "slack_notify_detail": detail[:200],
                        "http_status": put.status_code,
                    },
                )
                return "failed", detail

            r2 = client.post(
                "https://slack.com/api/files.completeUploadExternal",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "channel_id": channel,
                    "initial_comment": initial_comment,
                    "files": [{"id": file_id, "title": filename}],
                },
            )
            d2 = r2.json()
            if not _slack_api_ok(d2):
                detail = str(d2.get("error", "unknown"))[:200]
                logger.error(
                    "slack file upload failed",
                    extra={
                        "event": "slack_file_upload_failed",
                        "outcome": "failed",
                        "slack_file_upload_status": "failed",
                        "slack_api_step": "completeUploadExternal",
                        "slack_notify_detail": detail,
                        "http_status": r2.status_code,
                    },
                )
                return "failed", detail

        logger.info(
            "slack file upload complete",
            extra={
                "event": "slack_file_upload_complete",
                "outcome": "ok",
                "slack_file_upload_status": "ok",
                "slack_webhook_host": host,
            },
        )
        return "ok", "slack_files_upload_ok"
    except httpx.TimeoutException:
        detail = "timeout"
        logger.error(
            "slack file upload failed",
            extra={
                "event": "slack_file_upload_failed",
                "outcome": "failed",
                "slack_file_upload_status": "failed",
                "slack_webhook_host": host,
                "error_type": "timeout",
                "slack_notify_detail": detail,
            },
        )
        return "failed", detail
    except httpx.RequestError as e:
        detail = "request_error"
        logger.error(
            "slack file upload failed",
            extra={
                "event": "slack_file_upload_failed",
                "outcome": "failed",
                "slack_file_upload_status": "failed",
                "slack_webhook_host": host,
                "error_type": type(e).__name__,
                "slack_notify_detail": detail,
            },
        )
        return "failed", detail


def upload_report_pdf_to_slack(
    *,
    settings: Settings,
    pdf_bytes: bytes,
    filename: str,
    initial_comment: str,
    logger: logging.Logger,
    timeout_seconds: float,
) -> tuple[SlackPdfUploadStatus, str]:
    """Backward-compatible alias for ``upload_file_to_slack_channel`` (PDF)."""
    return upload_file_to_slack_channel(
        settings=settings,
        file_bytes=pdf_bytes,
        filename=filename,
        initial_comment=initial_comment,
        logger=logger,
        timeout_seconds=timeout_seconds,
    )
