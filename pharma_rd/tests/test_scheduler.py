"""Recurring scheduler (story 2.1 / FR2)."""

from __future__ import annotations

import pytest
from apscheduler.schedulers.blocking import BlockingScheduler
from pharma_rd.config import Settings
from pydantic import ValidationError


def test_cron_trigger_from_settings_default() -> None:
    from pharma_rd.config import get_settings
    from pharma_rd.scheduler import cron_trigger_from_settings

    get_settings.cache_clear()
    t = cron_trigger_from_settings(get_settings())
    assert t is not None


def test_run_scheduler_invalid_cron_exits_nonzero(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "s.db"))
    monkeypatch.setenv("PHARMA_RD_SCHEDULE_CRON", "this is not valid cron")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()
    from pharma_rd.scheduler import run_scheduler

    rc = run_scheduler()
    assert rc == 1
    err = capsys.readouterr().err
    assert "invalid" in err.lower() or "schedule" in err.lower()


def test_scheduled_pipeline_run_job_calls_execute_without_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def fake_execute(**kw) -> int:
        calls.append(kw)
        return 0

    monkeypatch.setattr("pharma_rd.scheduler.execute_pipeline_run", fake_execute)
    from pharma_rd.scheduler import scheduled_pipeline_run_job

    scheduled_pipeline_run_job()
    assert calls == [
        {"emit_summary_json": False, "enforce_cli_access": False},
    ]


def test_scheduler_timezone_must_be_valid_iana() -> None:
    with pytest.raises(ValidationError, match="IANA"):
        Settings(scheduler_timezone="NotAReal/Zone")


def test_run_scheduler_happy_path_registers_job(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "h.db"))
    monkeypatch.setenv("PHARMA_RD_SCHEDULE_CRON", "0 0 * * sun")
    monkeypatch.setenv("PHARMA_RD_SCHEDULER_TIMEZONE", "UTC")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    add_jobs: list[tuple] = []

    def capture_add(self, *args, **kwargs) -> None:
        add_jobs.append((args, kwargs))

    def interrupt_start(self) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(BlockingScheduler, "add_job", capture_add)
    monkeypatch.setattr(BlockingScheduler, "start", interrupt_start)

    from pharma_rd.scheduler import run_scheduler

    rc = run_scheduler()
    assert rc == 0
    assert len(add_jobs) == 1


def test_execute_pipeline_run_respects_emit_flag(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scheduled path does not print summary JSON (stdout policy)."""
    monkeypatch.setenv("PHARMA_RD_DB_PATH", str(tmp_path / "e.db"))
    monkeypatch.setenv("PHARMA_RD_ARTIFACTS_ROOT", str(tmp_path / "art"))
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    def no_pipeline(*_a, **_k) -> None:
        return None

    monkeypatch.setattr("pharma_rd.cli.run_pipeline", no_pipeline)

    from pharma_rd.cli import execute_pipeline_run

    rc = execute_pipeline_run(emit_summary_json=False, enforce_cli_access=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip() == "" or "run_id" not in out
