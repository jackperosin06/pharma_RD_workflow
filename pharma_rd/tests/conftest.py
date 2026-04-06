"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from pharma_rd.config import get_settings


@pytest.fixture(autouse=True)
def _pharma_rd_test_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tests; default synthesis to deterministic (no OpenAI key in CI).

    Do not name this fixture ``_clear_settings_cache`` — test modules define that
    name for cache-only teardown; same name would shadow this fixture and skip
    env overrides.
    """
    monkeypatch.setenv("PHARMA_RD_SYNTHESIS_MODE", "deterministic")
    monkeypatch.setenv("PHARMA_RD_REPORT_RENDERER", "template")
    # Local `pharma_rd/.env` may set secrets; empty env overrides dotenv.
    monkeypatch.setenv("PHARMA_RD_OPENAI_API_KEY", "")
    monkeypatch.setenv("PHARMA_RD_SLACK_WEBHOOK_URL", "")
    monkeypatch.setenv("PHARMA_RD_REPORT_PDF_ENABLED", "false")
    monkeypatch.setenv("PHARMA_RD_REPORT_DOCX_ENABLED", "false")
    monkeypatch.setenv("PHARMA_RD_CLINICAL_FIXTURE_PATH", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
