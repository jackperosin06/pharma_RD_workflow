"""Settings validation (PHARMA_RD_*)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_log_level_invalid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_LOG_LEVEL", "FOO")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="log_level must be one of"):
        get_settings()


def test_connector_probe_url_empty_becomes_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_CONNECTOR_PROBE_URL", "   ")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().connector_probe_url is None


def test_log_level_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_LOG_LEVEL", "debug")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().log_level == "DEBUG"


def test_therapeutic_area_labels_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_THERAPEUTIC_AREAS", " diabetes , oncology ")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().therapeutic_area_labels() == ["diabetes", "oncology"]


def test_competitor_labels_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_COMPETITOR_WATCHLIST",
        " Acme , BetaPharma ",
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().competitor_labels() == ["Acme", "BetaPharma"]


def test_pipeline_disclosure_scope_labels_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES",
        " Oncology , Rare disease ",
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().pipeline_disclosure_scope_labels() == [
        "Oncology",
        "Rare disease",
    ]
