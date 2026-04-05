"""Consumer agent — FR11 / FR26."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pharma_rd.agents.consumer import _SKIP_KEY_NOTE, run_consumer
from pharma_rd.config import get_settings
from pharma_rd.pipeline.contracts import CompetitorOutput, ConsumerGptAnalysis


def _minimal_competitor(run_id: str) -> CompetitorOutput:
    return CompetitorOutput(run_id=run_id)


def test_run_consumer_practice_mock_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    get_settings.cache_clear()
    out = run_consumer("rid-1", _minimal_competitor("rid-1"))
    assert out.schema_version == 5
    assert _SKIP_KEY_NOTE in out.integration_notes
    assert out.consumer_gpt_analysis is None
    assert out.run_id == "rid-1"
    assert out.practice_mode is True
    assert len(out.feedback_themes) == 1
    assert out.feedback_themes[0].source.startswith("practice://")
    assert any("FR26" in n for n in out.integration_notes)
    assert any(
        "FR12" in n and "PHARMA_RD_PHARMACY_SALES_PATH" in n
        for n in out.integration_notes
    )
    assert any(
        "FR13" in n and "PHARMA_RD_UNMET_NEED_DEMAND_PATH" in n
        for n in out.integration_notes
    )
    assert out.pharmacy_sales_trends == []
    assert out.unmet_need_demand_signals == []
    assert not out.data_gaps


def test_run_consumer_fixture_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "consumer_feedback"
        / "sample.json"
    )
    monkeypatch.setenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", str(fixture))
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    get_settings.cache_clear()
    out = run_consumer("rid-2", _minimal_competitor("rid-2"))
    assert out.practice_mode is True
    assert len(out.feedback_themes) == 2
    assert out.feedback_themes[0].theme == "taste and flavor"
    assert any("fixture" in n.lower() for n in out.integration_notes)


def test_run_consumer_no_mock_no_path_has_gaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.setenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", "false")
    get_settings.cache_clear()
    out = run_consumer("rid-3", _minimal_competitor("rid-3"))
    assert out.practice_mode is False
    assert out.feedback_themes == []
    assert out.data_gaps
    assert "NFR-I1" in out.data_gaps[0]


def test_fixture_malformed_theme_row(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "feedback_themes": [
                    {"theme": "", "summary": "x", "source": "s"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", str(bad))
    get_settings.cache_clear()
    out = run_consumer("rid-4", _minimal_competitor("rid-4"))
    assert out.feedback_themes == []
    assert any("invalid" in g.lower() or "theme" in g.lower() for g in out.data_gaps)


def test_fixture_null_feedback_themes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    n = tmp_path / "null.json"
    n.write_text(json.dumps({"feedback_themes": None}), encoding="utf-8")
    monkeypatch.setenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", str(n))
    get_settings.cache_clear()
    out = run_consumer("rid-5", _minimal_competitor("rid-5"))
    assert out.feedback_themes == []
    assert any("null" in g or "missing" in g for g in out.data_gaps)


def test_pharmacy_sales_fixture_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "pharmacy_sales"
        / "sample.json"
    )
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_PHARMACY_SALES_PATH", str(fixture))
    get_settings.cache_clear()
    out = run_consumer("rid-sales-1", _minimal_competitor("rid-sales-1"))
    assert len(out.pharmacy_sales_trends) == 2
    assert out.pharmacy_sales_trends[0].scope == "US pharmacy retail"
    assert out.pharmacy_sales_trends[0].period == "2025-Q4"
    assert out.pharmacy_sales_trends[1].scope == "Regional wholesale"
    assert any("FR12" in n for n in out.integration_notes)


def test_pharmacy_sales_empty_fixture_transparent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(
        json.dumps({"pharmacy_sales_trends": []}),
        encoding="utf-8",
    )
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_PHARMACY_SALES_PATH", str(empty))
    get_settings.cache_clear()
    out = run_consumer("rid-sales-2", _minimal_competitor("rid-sales-2"))
    assert out.pharmacy_sales_trends == []
    assert any("empty" in n.lower() for n in out.integration_notes)


def test_pharmacy_sales_period_numeric_coerced(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    p = tmp_path / "num.json"
    p.write_text(
        json.dumps(
            {
                "pharmacy_sales_trends": [
                    {
                        "summary": "Units steady.",
                        "scope": "Test market",
                        "period": 2025,
                        "source": "fixture",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_PHARMACY_SALES_PATH", str(p))
    get_settings.cache_clear()
    out = run_consumer("rid-sales-4", _minimal_competitor("rid-sales-4"))
    assert len(out.pharmacy_sales_trends) == 1
    assert out.pharmacy_sales_trends[0].period == "2025"


def test_unmet_need_demand_fixture_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "unmet_need_demand"
        / "sample.json"
    )
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_UNMET_NEED_DEMAND_PATH", str(fixture))
    get_settings.cache_clear()
    out = run_consumer("rid-ud-1", _minimal_competitor("rid-ud-1"))
    assert len(out.unmet_need_demand_signals) == 2
    assert out.unmet_need_demand_signals[0].signal == "Faster onset pain relief"
    assert (
        out.unmet_need_demand_signals[0].source == "market-scan://example/category-q4"
    )
    assert any("FR13" in n for n in out.integration_notes)


def test_unmet_need_demand_empty_fixture_transparent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(
        json.dumps({"unmet_need_demand_signals": []}),
        encoding="utf-8",
    )
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_UNMET_NEED_DEMAND_PATH", str(empty))
    get_settings.cache_clear()
    out = run_consumer("rid-ud-2", _minimal_competitor("rid-ud-2"))
    assert out.unmet_need_demand_signals == []
    assert any("empty" in n.lower() for n in out.integration_notes)


def test_unmet_need_demand_null_signals_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    n = tmp_path / "null.json"
    n.write_text(json.dumps({"unmet_need_demand_signals": None}), encoding="utf-8")
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_UNMET_NEED_DEMAND_PATH", str(n))
    get_settings.cache_clear()
    out = run_consumer("rid-ud-3", _minimal_competitor("rid-ud-3"))
    assert out.unmet_need_demand_signals == []
    assert any("null" in g or "missing" in g for g in out.data_gaps)


def test_unmet_need_demand_path_missing_gap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv(
        "PHARMA_RD_UNMET_NEED_DEMAND_PATH",
        str(tmp_path / "nonexistent.json"),
    )
    get_settings.cache_clear()
    out = run_consumer("rid-ud-4", _minimal_competitor("rid-ud-4"))
    assert out.unmet_need_demand_signals == []
    assert any("does not exist" in g for g in out.data_gaps)


def test_pharmacy_sales_path_missing_gap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv(
        "PHARMA_RD_PHARMACY_SALES_PATH",
        str(tmp_path / "nonexistent.json"),
    )
    get_settings.cache_clear()
    out = run_consumer("rid-sales-3", _minimal_competitor("rid-sales-3"))
    assert out.pharmacy_sales_trends == []
    assert any("does not exist" in g for g in out.data_gaps)


def test_run_consumer_gpt_enrichment_mocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gpt = ConsumerGptAnalysis(
        unmet_need_synthesis="U",
        demand_pattern_summary="D",
        line_extension_relevance="L",
    )
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    with patch(
        "pharma_rd.agents.consumer.call_consumer_gpt_analysis",
        return_value=(gpt, None),
    ):
        out = run_consumer("rid-gpt", _minimal_competitor("rid-gpt"))
    assert out.consumer_gpt_analysis == gpt
    assert _SKIP_KEY_NOTE not in out.integration_notes


def test_run_consumer_gpt_failure_degrades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PHARMA_RD_CONSUMER_FEEDBACK_PATH", raising=False)
    monkeypatch.delenv("PHARMA_RD_PRACTICE_CONSUMER_MOCK", raising=False)
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    with patch(
        "pharma_rd.agents.consumer.call_consumer_gpt_analysis",
        return_value=(None, "RateLimitError: 429"),
    ):
        out = run_consumer("rid-gpt-fail", _minimal_competitor("rid-gpt-fail"))
    assert out.consumer_gpt_analysis is None
    assert any(
        "GPT consumer insight analysis failed" in n for n in out.integration_notes
    )
    assert any("RateLimitError" in g for g in out.data_gaps)
