"""FR19 report distribution (file drop, none, smtp placeholder)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from pharma_rd.config import get_settings
from pharma_rd.integrations.report_distribution import distribute_insight_report
from pharma_rd.logging_setup import get_pipeline_logger
from pharma_rd.readability import validate_readable_insight_report


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_distribute_none_skipped(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "none")
    get_settings.cache_clear()
    ch, st, det = distribute_insight_report(
        "run-a",
        tmp_path,
        settings=get_settings(),
        logger=get_pipeline_logger("test.distribution"),
    )
    assert ch == "none"
    assert st == "skipped"
    assert "none" in det.lower()
    assert any(
        getattr(r, "event", None) == "distribution_skipped" for r in caplog.records
    )


def test_distribute_file_drop_copies_and_manifest(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.INFO)
    art = tmp_path / "artifacts"
    drop = tmp_path / "drop"
    rid = "run-b"
    report = art / rid / "delivery" / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Report\n", encoding="utf-8")
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "file_drop")
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_DROP_DIR", str(drop))
    get_settings.cache_clear()
    ch, st, det = distribute_insight_report(
        rid,
        art,
        settings=get_settings(),
        logger=get_pipeline_logger("test.distribution"),
    )
    assert ch == "file_drop"
    assert st == "ok"
    rd_f = drop / "rd" / rid / "report.md"
    mk_f = drop / "marketing" / rid / "report.md"
    assert rd_f.read_text(encoding="utf-8") == "# Report\n"
    assert mk_f.read_text(encoding="utf-8") == "# Report\n"
    man = drop / rid / "manifest.json"
    payload = json.loads(man.read_text(encoding="utf-8"))
    assert payload["run_id"] == rid
    assert payload["rd_report_path"] == str(rd_f.resolve())
    assert payload["marketing_report_path"] == str(mk_f.resolve())
    assert payload["source_artifact_relative"] == f"{rid}/delivery/report.md"
    assert any(
        getattr(r, "event", None) == "distribution_complete" for r in caplog.records
    )
    assert "manifest=" in det


def test_distribute_file_drop_copies_html_and_manifest(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.INFO)
    art = tmp_path / "artifacts"
    drop = tmp_path / "drop"
    rid = "run-html"
    report = art / rid / "delivery" / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text(
        "## Run summary\n\n## Ranked opportunities\n(none)\n"
        "## Governance and disclaimer\nx\n",
        encoding="utf-8",
    )
    html = art / rid / "delivery" / "report.html"
    html.write_text("<!DOCTYPE html><html><body>ok</body></html>\n", encoding="utf-8")
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "file_drop")
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_DROP_DIR", str(drop))
    get_settings.cache_clear()
    ch, st, _det = distribute_insight_report(
        rid,
        art,
        settings=get_settings(),
        logger=get_pipeline_logger("test.distribution"),
    )
    assert ch == "file_drop"
    assert st == "ok"
    rd_md = drop / "rd" / rid / "report.md"
    assert rd_md.read_bytes() == report.read_bytes()
    rd_h = drop / "rd" / rid / "report.html"
    assert rd_h.read_bytes() == html.read_bytes()
    man = json.loads((drop / rid / "manifest.json").read_text(encoding="utf-8"))
    assert man["rd_report_html_path"] == str(rd_h.resolve())
    assert man["source_artifact_html_relative"] == f"{rid}/delivery/report.html"
    validate_readable_insight_report(rd_md)


def test_distribute_file_drop_missing_drop_dir(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.ERROR)
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "file_drop")
    monkeypatch.delenv("PHARMA_RD_DISTRIBUTION_DROP_DIR", raising=False)
    get_settings.cache_clear()
    ch, st, det = distribute_insight_report(
        "r",
        tmp_path,
        settings=get_settings(),
        logger=get_pipeline_logger("test.distribution"),
    )
    assert ch == "file_drop"
    assert st == "failed"
    assert "DISTRIBUTION_DROP_DIR" in det
    assert any(
        getattr(r, "event", None) == "distribution_failed" for r in caplog.records
    )
    failed = next(
        r for r in caplog.records if getattr(r, "event", None) == "distribution_failed"
    )
    assert getattr(failed, "error_type", None) == "missing_drop_dir"


def test_distribute_file_drop_rejects_unsafe_run_id(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.ERROR)
    art = tmp_path / "artifacts"
    drop = tmp_path / "drop"
    rid = "evil/../escape"
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "file_drop")
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_DROP_DIR", str(drop))
    get_settings.cache_clear()
    ch, st, det = distribute_insight_report(
        rid,
        art,
        settings=get_settings(),
        logger=get_pipeline_logger("test.distribution"),
    )
    assert ch == "file_drop"
    assert st == "failed"
    assert "run_id" in det.lower()
    failed = next(
        r for r in caplog.records if getattr(r, "event", None) == "distribution_failed"
    )
    assert getattr(failed, "error_type", None) == "invalid_run_id"


def test_distribute_file_drop_missing_report(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.ERROR)
    art = tmp_path / "artifacts"
    drop = tmp_path / "drop"
    rid = "run-c"
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "file_drop")
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_DROP_DIR", str(drop))
    get_settings.cache_clear()
    ch, st, _det = distribute_insight_report(
        rid,
        art,
        settings=get_settings(),
        logger=get_pipeline_logger("test.distribution"),
    )
    assert ch == "file_drop"
    assert st == "failed"
    assert any(
        getattr(r, "event", None) == "distribution_failed" for r in caplog.records
    )
    failed = next(
        r for r in caplog.records if getattr(r, "event", None) == "distribution_failed"
    )
    assert getattr(failed, "error_type", None) == "missing_report"


def test_distribute_smtp_not_implemented(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.ERROR)
    monkeypatch.setenv("PHARMA_RD_DISTRIBUTION_CHANNEL", "smtp")
    get_settings.cache_clear()
    ch, st, det = distribute_insight_report(
        "r",
        tmp_path,
        settings=get_settings(),
        logger=get_pipeline_logger("test.distribution"),
    )
    assert ch == "smtp"
    assert st == "failed"
    assert "MVP" in det
    assert any(
        getattr(r, "event", None) == "distribution_failed" for r in caplog.records
    )
    failed = next(
        r for r in caplog.records if getattr(r, "event", None) == "distribution_failed"
    )
    assert getattr(failed, "error_type", None) == "smtp_not_implemented"
