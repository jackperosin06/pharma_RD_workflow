"""Internal research JSON loader (FR7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pharma_rd.config import get_settings
from pharma_rd.integrations.internal_research import ingest_internal_research


@pytest.fixture
def internal_sample_json() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "internal_research"
        / "sample.json"
    )


def test_ingest_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHARMA_RD_INTERNAL_RESEARCH_PATH", raising=False)
    get_settings.cache_clear()
    s = get_settings()
    items, notes, gaps = ingest_internal_research(s)
    assert items == []
    assert gaps == []
    assert any("not configured" in n.lower() for n in notes)


def test_ingest_fixture_file(
    monkeypatch: pytest.MonkeyPatch,
    internal_sample_json: Path,
) -> None:
    monkeypatch.setenv("PHARMA_RD_INTERNAL_RESEARCH_PATH", str(internal_sample_json))
    get_settings.cache_clear()
    s = get_settings()
    items, notes, gaps = ingest_internal_research(s)
    assert len(items) == 1
    assert items[0].title == "Practice-mode internal summary"
    assert "fixture" in items[0].source_label
    assert not gaps or all("exceeds" not in g for g in gaps)


def test_ingest_missing_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "nope"
    monkeypatch.setenv("PHARMA_RD_INTERNAL_RESEARCH_PATH", str(missing))
    get_settings.cache_clear()
    s = get_settings()
    items, notes, gaps = ingest_internal_research(s)
    assert items == []
    assert any("does not exist" in g for g in gaps)


def test_ingest_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("PHARMA_RD_INTERNAL_RESEARCH_PATH", str(bad))
    get_settings.cache_clear()
    s = get_settings()
    items, notes, gaps = ingest_internal_research(s)
    assert items == []
    assert any("invalid json" in g.lower() for g in gaps)


def test_ingest_directory_two_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "a.json").write_text(
        json.dumps(
            {
                "title": "A",
                "summary": "Sa",
                "reference": "r1",
                "source_label": "t",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "b.json").write_text(
        json.dumps(
            {
                "title": "B",
                "summary": "Sb",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PHARMA_RD_INTERNAL_RESEARCH_PATH", str(tmp_path))
    get_settings.cache_clear()
    s = get_settings()
    items, notes, gaps = ingest_internal_research(s)
    assert len(items) == 2
    titles = {x.title for x in items}
    assert titles == {"A", "B"}
