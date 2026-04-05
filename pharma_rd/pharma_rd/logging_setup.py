"""Structured JSON logs to stdout — correlation per run, stage context (story 1.4).

``correlation_id`` equals ``run_id`` for MVP; external correlation is a future story.
"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from pharma_rd.config import get_settings

_run_id_ctx: ContextVar[str | None] = ContextVar("pharma_rd_run_id", default=None)
_correlation_id_ctx: ContextVar[str | None] = ContextVar(
    "pharma_rd_correlation_id", default=None
)
_stage_ctx: ContextVar[str | None] = ContextVar("pharma_rd_stage", default=None)
_agent_ctx: ContextVar[str | None] = ContextVar("pharma_rd_agent", default=None)

_configured = False


class PipelineContextFilter(logging.Filter):
    """Fill run_id, correlation_id, stage, agent from contextvars or extras."""

    def filter(self, record: logging.LogRecord) -> bool:
        rid = getattr(record, "run_id", None) or _run_id_ctx.get()
        if rid is not None:
            record.run_id = rid
            cid = getattr(record, "correlation_id", None) or _correlation_id_ctx.get()
            record.correlation_id = cid if cid is not None else rid
        st = getattr(record, "stage", None)
        if st is None:
            st = _stage_ctx.get()
        if st is not None:
            record.stage = st
            ag = getattr(record, "agent", None) or _agent_ctx.get() or st
            record.agent = ag
        elif getattr(record, "agent", None) is None:
            ag2 = _agent_ctx.get()
            if ag2 is not None:
                record.agent = ag2
        return True


class _StdoutJsonHandler(logging.Handler):
    """Always writes to the current ``sys.stdout`` (safe with pytest capture)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            sys.stdout.write(msg)
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


class JsonLineFormatter(logging.Formatter):
    """One JSON object per line (stdout), snake_case keys."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        payload: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "message": record.getMessage(),
            "run_id": getattr(record, "run_id", None),
            "correlation_id": getattr(record, "correlation_id", None),
            "stage": getattr(record, "stage", None),
            "agent": getattr(record, "agent", None),
            "event": getattr(record, "event", None),
            "outcome": getattr(record, "outcome", None),
        }
        for opt in (
            "completed_stage_count",
            "run_status",
            "error_type",
            "integration_error_class",
            "attempt",
            "max_attempts",
            "next_backoff_s",
            "http_status",
            "previous_sha256",
            "new_sha256",
            "resumed_from_stage",
            "deployment_profile",
            "feedback_theme_count",
            "practice_mode",
            "sales_trend_count",
            "unmet_need_demand_count",
            "upstream_gap_count",
            "snapshot_ok",
            "ranked_count",
            "ranking_criteria_version",
            "evidence_ref_count",
            "signal_characterization",
            "scan_summary_line_count",
            "report_relative_path",
            "report_byte_size",
            "report_html_relative_path",
            "report_html_byte_size",
            "distribution_channel",
            "distribution_status",
            "distribution_detail",
            "slack_notify_status",
            "slack_notify_detail",
            "slack_webhook_configured",
            "slack_webhook_host",
        ):
            if hasattr(record, opt):
                payload[opt] = getattr(record, opt)
        return json.dumps(payload, ensure_ascii=False) + "\n"


def configure_pipeline_logging() -> None:
    """Idempotent: wire ``pharma_rd`` logger to stdout with JSON lines."""
    global _configured
    if _configured:
        return
    _configured = True
    settings = get_settings()
    level = getattr(logging, settings.log_level)

    handler = _StdoutJsonHandler()
    handler.setFormatter(JsonLineFormatter())
    handler.addFilter(PipelineContextFilter())

    root = logging.getLogger("pharma_rd")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_pipeline_logger(name: str) -> logging.Logger:
    """Child loggers inherit ``pharma_rd`` handlers (propagate=True by default)."""
    return logging.getLogger(name)


@contextmanager
def pipeline_run_logging(run_id: str):
    """Bind ``run_id`` and ``correlation_id`` (same value) for one pipeline run."""
    t1: Token[str | None] = _run_id_ctx.set(run_id)
    t2: Token[str | None] = _correlation_id_ctx.set(run_id)
    try:
        yield
    finally:
        _run_id_ctx.reset(t1)
        _correlation_id_ctx.reset(t2)


@contextmanager
def stage_logging(stage_key: str):
    """Bind ``stage`` and ``agent`` (same string as stage for stubs)."""
    t1: Token[str | None] = _stage_ctx.set(stage_key)
    t2: Token[str | None] = _agent_ctx.set(stage_key)
    try:
        yield
    finally:
        _stage_ctx.reset(t1)
        _agent_ctx.reset(t2)


def log_agent_stub(
    logger: logging.Logger,
    *,
    message: str = "stub agent executed",
) -> None:
    """One minimal stage-scoped line from stub agents (tests assert correlation)."""
    logger.info(
        message,
        extra={"event": "agent_stub", "outcome": "ok"},
    )
