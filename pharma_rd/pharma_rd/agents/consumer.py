"""Consumer Insight agent — FR11–FR13 (feedback, sales, demand signals); FR26."""

from __future__ import annotations

from pharma_rd.agents.connector_probe import ensure_connector_probe
from pharma_rd.config import Settings, get_settings
from pharma_rd.integrations.consumer_feedback import ingest_consumer_feedback_fixture
from pharma_rd.integrations.openai_consumer import call_consumer_gpt_analysis
from pharma_rd.integrations.pharmacy_sales import ingest_pharmacy_sales_fixture
from pharma_rd.integrations.unmet_need_demand import ingest_unmet_need_demand_fixture
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.pipeline.contracts import (
    CompetitorOutput,
    ConsumerFeedbackThemeItem,
    ConsumerOutput,
    PharmacySalesTrendItem,
    UnmetNeedDemandSignalItem,
)

_log = get_pipeline_logger("pharma_rd.agents.consumer")

_SKIP_KEY_NOTE = (
    "GPT consumer insight analysis skipped: PHARMA_RD_OPENAI_API_KEY not set "
    "(story 5.4)."
)
_SKIP_EMPTY_NOTE = (
    "GPT consumer insight analysis skipped: no consumer signal rows to analyze "
    "(story 5.4)."
)


def _append_note_once(out: ConsumerOutput, note: str) -> ConsumerOutput:
    if note in out.integration_notes:
        return out
    return out.model_copy(
        update={"integration_notes": list(out.integration_notes) + [note]}
    )


def _apply_consumer_gpt(out: ConsumerOutput, settings: Settings) -> ConsumerOutput:
    """Story 5.4: optional GPT-4o market analyst pass (matches stories 3.3 / 4.4)."""
    if not settings.openai_api_key:
        return _append_note_once(out, _SKIP_KEY_NOTE)

    if (
        not out.feedback_themes
        and not out.pharmacy_sales_trends
        and not out.unmet_need_demand_signals
    ):
        return _append_note_once(out, _SKIP_EMPTY_NOTE)

    gpt, err = call_consumer_gpt_analysis(settings, out)
    if gpt is not None:
        _log.info(
            "consumer gpt analysis completed",
            extra={"event": "consumer_gpt_analysis", "outcome": "ok"},
        )
        return out.model_copy(update={"consumer_gpt_analysis": gpt})

    _log.warning(
        "consumer gpt analysis failed",
        extra={
            "event": "consumer_gpt_analysis",
            "outcome": "failed",
            "error_class": "openai",
        },
    )
    notes = list(out.integration_notes)
    gaps = list(out.data_gaps)
    notes.append(
        "GPT consumer insight analysis failed (OpenAI). Proceeding with fetch-only "
        f"output (NFR-I1). Detail: {err}"
    )
    gaps.append(f"GPT consumer insight analysis unavailable: {err}")
    return out.model_copy(update={"integration_notes": notes, "data_gaps": gaps})


def _practice_mock_themes() -> list[ConsumerFeedbackThemeItem]:
    """Built-in themes when no fixture is configured (FR26)."""
    return [
        ConsumerFeedbackThemeItem(
            theme="product experience (practice mock)",
            summary=(
                "Placeholder consumer themes for pipeline demos. Configure "
                "PHARMA_RD_CONSUMER_FEEDBACK_PATH for JSON fixtures."
            ),
            source="practice://consumer-mock",
        )
    ]


def run_consumer(run_id: str, competitor: CompetitorOutput) -> ConsumerOutput:
    """Surface FR11 themes, FR12 pharmacy sales, FR13 unmet-need/demand; FR26."""
    _ = competitor
    ensure_connector_probe("consumer")
    settings = get_settings()
    notes: list[str] = []
    gaps: list[str] = []
    themes: list[ConsumerFeedbackThemeItem] = []
    practice_mode: bool

    if settings.consumer_feedback_path is not None:
        themes, fnotes, fgaps = ingest_consumer_feedback_fixture(settings)
        notes.extend(fnotes)
        gaps.extend(fgaps)
        practice_mode = True
        if not themes and not fgaps:
            gaps.append(
                "Consumer feedback: fixture path set but no themes were loaded "
                "(NFR-I1)."
            )
    elif settings.practice_consumer_mock:
        practice_mode = True
        themes = _practice_mock_themes()
        notes.append(
            "Consumer feedback source: practice mock (FR26). "
            "Set PHARMA_RD_CONSUMER_FEEDBACK_PATH to use JSON fixtures."
        )
    else:
        practice_mode = False
        gaps.append(
            "Consumer feedback not configured: PHARMA_RD_PRACTICE_CONSUMER_MOCK is "
            "false and PHARMA_RD_CONSUMER_FEEDBACK_PATH is unset (NFR-I1)."
        )

    sales_trends: list[PharmacySalesTrendItem] = []
    if settings.pharmacy_sales_path is not None:
        strends, snotes, sgaps = ingest_pharmacy_sales_fixture(settings)
        sales_trends.extend(strends)
        notes.extend(snotes)
        gaps.extend(sgaps)
    else:
        notes.append(
            "Pharmacy sales (FR12): feed not configured; set "
            "PHARMA_RD_PHARMACY_SALES_PATH for JSON fixtures (NFR-I1)."
        )

    demand_signals: list[UnmetNeedDemandSignalItem] = []
    if settings.unmet_need_demand_path is not None:
        dsigs, dnotes, dgaps = ingest_unmet_need_demand_fixture(settings)
        demand_signals.extend(dsigs)
        notes.extend(dnotes)
        gaps.extend(dgaps)
    else:
        notes.append(
            "Unmet need / demand (FR13): market feed not configured; set "
            "PHARMA_RD_UNMET_NEED_DEMAND_PATH for JSON fixtures (NFR-I1)."
        )

    base = ConsumerOutput(
        run_id=run_id,
        feedback_themes=themes,
        pharmacy_sales_trends=sales_trends,
        unmet_need_demand_signals=demand_signals,
        practice_mode=practice_mode,
        data_gaps=gaps,
        integration_notes=notes,
    )

    _log.info(
        "consumer feedback processed",
        extra={
            "event": "consumer_feedback",
            "outcome": "ok",
            "feedback_theme_count": len(themes),
            "practice_mode": practice_mode,
        },
    )
    _log.info(
        "pharmacy sales trends processed",
        extra={
            "event": "consumer_pharmacy_sales",
            "outcome": "ok",
            "sales_trend_count": len(sales_trends),
        },
    )
    _log.info(
        "unmet need / demand signals processed",
        extra={
            "event": "consumer_unmet_need_demand",
            "outcome": "ok",
            "unmet_need_demand_count": len(demand_signals),
        },
    )
    return _apply_consumer_gpt(base, settings)
