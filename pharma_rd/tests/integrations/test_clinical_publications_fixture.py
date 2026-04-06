"""Clinical publication JSON fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from pharma_rd.config import get_settings
from pharma_rd.integrations.clinical_publications_fixture import (
    ingest_clinical_publication_fixture,
)

_SAMPLE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "clinical"
    / "sample.json"
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_ingest_clinical_fixture_loads_publications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_CLINICAL_FIXTURE_PATH", str(_SAMPLE))
    get_settings.cache_clear()
    s = get_settings()
    items, notes, gaps = ingest_clinical_publication_fixture(s)
    assert len(items) == 10
    assert not gaps
    assert any("no live pubmed" in n.lower() for n in notes)
    assert all(p.source == "pubmed" for p in items)
    assert items[0].reference.startswith("https://pubmed.ncbi.nlm.nih.gov/")


def test_ingest_clinical_fixture_unset_returns_empty() -> None:
    get_settings.cache_clear()
    s = get_settings()
    items, notes, gaps = ingest_clinical_publication_fixture(s)
    assert items == [] and notes == [] and gaps == []
