"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from pharma_rd.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tests; default synthesis to deterministic (no OpenAI key in CI)."""
    monkeypatch.setenv("PHARMA_RD_SYNTHESIS_MODE", "deterministic")
    monkeypatch.setenv("PHARMA_RD_REPORT_RENDERER", "template")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
