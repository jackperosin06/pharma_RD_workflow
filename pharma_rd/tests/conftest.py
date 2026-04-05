"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from pharma_rd.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Isolate tests that mutate PHARMA_RD_* environment variables."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
