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
    assert get_settings().therapeutic_areas == "diabetes, oncology"


def test_therapeutic_areas_empty_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_THERAPEUTIC_AREAS", "   ")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().therapeutic_area_labels() == []


def test_therapeutic_areas_invalid_empty_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_THERAPEUTIC_AREAS", "a,,b")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="empty label between commas"):
        get_settings()


def test_therapeutic_areas_invalid_character(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_THERAPEUTIC_AREAS", "oncology&diabetes")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="disallowed characters"):
        get_settings()


def test_therapeutic_areas_label_too_long(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_THERAPEUTIC_AREAS",
        "x" * 129,
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="exceeds max length"):
        get_settings()


def test_therapeutic_areas_too_many_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_THERAPEUTIC_AREAS",
        ",".join(f"a{i}" for i in range(33)),
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="too many labels"):
        get_settings()


def test_competitor_labels_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_COMPETITOR_WATCHLIST",
        " Acme , BetaPharma ",
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().competitor_labels() == ["Acme", "BetaPharma"]
    assert get_settings().competitor_watchlist == "Acme, BetaPharma"


def test_competitor_watchlist_corporate_chars_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_COMPETITOR_WATCHLIST",
        "Johnson & Johnson (EU), Acme Corp.",
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().competitor_labels() == [
        "Johnson & Johnson (EU)",
        "Acme Corp.",
    ]


def test_competitor_watchlist_empty_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_COMPETITOR_WATCHLIST", "  ")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().competitor_labels() == []


def test_competitor_watchlist_invalid_empty_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_COMPETITOR_WATCHLIST", "a,,b")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="empty label between"):
        get_settings()


def test_competitor_watchlist_invalid_character(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_COMPETITOR_WATCHLIST", "Acme;Beta")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="disallowed characters"):
        get_settings()


def test_competitor_watchlist_label_too_long(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_COMPETITOR_WATCHLIST", "x" * 129)
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="exceeds max length"):
        get_settings()


def test_competitor_watchlist_too_many_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_COMPETITOR_WATCHLIST",
        ",".join(f"a{i}" for i in range(33)),
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="too many labels"):
        get_settings()


def test_pubmed_eutils_base_invalid_url_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_PUBMED_EUTILS_BASE", "not-a-url")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="PUBMED_EUTILS_BASE"):
        get_settings()


def test_openfda_url_invalid_scheme_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_OPENFDA_DRUGSFDA_URL", "ftp://api.fda.gov/x")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="OPENFDA_DRUGSFDA_URL"):
        get_settings()


def test_connector_probe_url_invalid_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_CONNECTOR_PROBE_URL", "not-a-url")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="CONNECTOR_PROBE_URL"):
        get_settings()


def test_slack_webhook_url_must_be_https(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PHARMA_RD_SLACK_WEBHOOK_URL",
        "http://hooks.slack.com/services/x/y/z",
    )
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="https"):
        get_settings()


def test_artifact_access_token_too_long_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_ARTIFACT_ACCESS_TOKEN", "x" * 8193)
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="8192"):
        get_settings()


def test_deployment_profile_default_practice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PHARMA_RD_DEPLOYMENT_PROFILE", raising=False)
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().deployment_profile == "practice"


def test_deployment_profile_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DEPLOYMENT_PROFILE", "staging")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().deployment_profile == "staging"


def test_deployment_profile_invalid_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DEPLOYMENT_PROFILE", "enterprise")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="deployment_profile"):
        get_settings()


def test_openai_api_key_unset_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHARMA_RD_OPENAI_API_KEY", raising=False)
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().openai_api_key is None


def test_openai_api_key_whitespace_becomes_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "   ")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().openai_api_key is None


def test_openai_model_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHARMA_RD_OPENAI_MODEL", raising=False)
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().openai_model == "gpt-4o"


def test_insight_org_display_name_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHARMA_RD_INSIGHT_ORG_DISPLAY_NAME", raising=False)
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    assert get_settings().insight_org_display_name == "iNova"


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
