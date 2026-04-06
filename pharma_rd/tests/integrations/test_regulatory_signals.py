"""Regulatory fixture loader and OpenFDA client (FR8, FR10 patent flags)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pharma_rd.config import get_settings
from pharma_rd.http_client import ConnectorFailure, IntegrationErrorClass
from pharma_rd.integrations.regulatory_signals import (
    fetch_openfda_approvals,
    ingest_competitor_regulatory_fixture,
)


@pytest.fixture
def sample_fixture_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "competitor_regulatory"
        / "sample.json"
    )


def test_ingest_fixture_file(
    monkeypatch: pytest.MonkeyPatch,
    sample_fixture_path: Path,
) -> None:
    monkeypatch.setenv("PHARMA_RD_COMPETITOR_REGULATORY_PATH", str(sample_fixture_path))
    get_settings.cache_clear()
    a, d, p, pf, n, g = ingest_competitor_regulatory_fixture(get_settings())
    assert len(a) == 1
    assert len(d) == 1
    assert len(p) == 1
    assert p[0].scope_tags == ("Oncology",)
    assert len(pf) == 1
    assert pf[0].competitor_tags == ("AcmePharma",)
    assert not g
    assert any("loaded" in x.lower() for x in n)


def test_fetch_openfda_parses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_OPENFDA_DRUGSFDA_URL", "https://api.fda.gov/drug/drugsfda.json")
    get_settings.cache_clear()
    body = {
        "results": [
            {
                "sponsor_name": "Acme Corp",
                "application_number": "123456",
                "products": [{"brand_name": "DrugZ"}],
                "submissions": [
                    {"submission_status_date": "20240115", "submission_type": "ORIG"}
                ],
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = body
    with patch(
        "pharma_rd.integrations.regulatory_signals.request_with_retries",
        return_value=mock_resp,
    ):
        items, notes, gaps = fetch_openfda_approvals(["Acme"], settings=get_settings())
    assert len(items) == 1
    assert "Acme" in items[0].title or "DrugZ" in items[0].title
    assert items[0].reference.startswith("http")
    assert items[0].observed_at == "2024-01-15T00:00:00Z"
    assert not gaps


def test_fetch_openfda_not_found_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenFDA returns HTTP 404 + NOT_FOUND JSON when a search matches nothing."""
    monkeypatch.setenv("PHARMA_RD_OPENFDA_DRUGSFDA_URL", "https://api.fda.gov/drug/drugsfda.json")
    get_settings.cache_clear()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "error": {"code": "NOT_FOUND", "message": "No matches found!"}
    }
    mock_resp.status_code = 404
    with patch(
        "pharma_rd.integrations.regulatory_signals.request_with_retries",
        return_value=mock_resp,
    ):
        items, notes, gaps = fetch_openfda_approvals(
            ["NonexistentCo"],
            settings=get_settings(),
        )
    assert items == []
    assert not gaps
    assert any("NOT_FOUND" in n or "no records matched" in n for n in notes)


def test_fetch_openfda_raises_connector_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_COMPETITOR_WATCHLIST", "X")
    get_settings.cache_clear()

    def boom(*_a: object, **_k: object) -> None:
        raise ConnectorFailure(
            "bad",
            error_class=IntegrationErrorClass.HTTP_CLIENT_ERROR,
        )

    with patch(
        "pharma_rd.integrations.regulatory_signals.request_with_retries",
        side_effect=boom,
    ):
        with pytest.raises(ConnectorFailure, match="bad"):
            fetch_openfda_approvals(["Pfizer"], settings=get_settings())
