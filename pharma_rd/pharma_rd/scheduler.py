"""In-process cron scheduler for full pipeline runs (FR2 / story 2.1).

Uses APScheduler BlockingScheduler. Overlapping ticks are skipped (non-blocking lock).
Config changes require process restart (documented).
"""

from __future__ import annotations

import sys
import threading

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from pharma_rd.cli import execute_pipeline_run
from pharma_rd.config import Settings, get_settings
from pharma_rd.logging_setup import configure_pipeline_logging, get_pipeline_logger

_log = get_pipeline_logger("pharma_rd.scheduler")

_overlap = threading.Lock()


def cron_trigger_from_settings(settings: Settings) -> CronTrigger:
    """Build trigger; raises if ``schedule_cron`` is invalid for APScheduler."""
    return CronTrigger.from_crontab(
        settings.schedule_cron.strip(),
        timezone=settings.scheduler_timezone,
    )


def scheduled_pipeline_run_job() -> None:
    """APScheduler job: one full pipeline run; skips if previous still running."""
    if not _overlap.acquire(blocking=False):
        _log.warning(
            "skipped scheduled run: previous run still in progress",
            extra={"event": "scheduler_skip", "outcome": "skipped"},
        )
        return
    try:
        rc = execute_pipeline_run(emit_summary_json=False)
        if rc != 0:
            _log.error(
                "scheduled pipeline run exited with failure",
                extra={"event": "scheduler_run_failed", "outcome": "failed"},
            )
    finally:
        _overlap.release()


def run_scheduler() -> int:
    """Block forever; run pipeline on cron. Returns non-zero only for startup errors."""
    configure_pipeline_logging()
    settings = get_settings()
    try:
        trigger = cron_trigger_from_settings(settings)
    except Exception as e:
        print(
            f"pharma_rd scheduler: invalid schedule_cron or timezone: {e}",
            file=sys.stderr,
        )
        return 1
    msg = (
        f"scheduler started cron={settings.schedule_cron!r} "
        f"tz={settings.scheduler_timezone!r}"
    )
    _log.info(msg, extra={"event": "scheduler_started", "outcome": None})
    sched = BlockingScheduler(timezone=settings.scheduler_timezone)
    sched.add_job(
        scheduled_pipeline_run_job,
        trigger=trigger,
        id="pharma_rd_pipeline_cron",
        replace_existing=True,
    )
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        return 0
    return 0
