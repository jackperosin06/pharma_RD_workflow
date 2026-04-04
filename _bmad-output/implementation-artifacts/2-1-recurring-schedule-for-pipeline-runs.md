# Story 2.1: Recurring schedule for pipeline runs

Status: done

<!-- Optional: run Validate Story ([VS]) before dev-story for a quality check. -->

## Story

As a **workflow operator**,
I want **to configure a recurring schedule with weekly default**,
so that **reports run without manual triggers** (FR2).

## Acceptance criteria

1. **Given** schedule settings in configuration (cron expression or equivalent)
   **When** the scheduler process runs
   **Then** pipeline runs start according to the configured cadence with **weekly** as the documented default
   **And** schedule changes take effect without code deploy (**config reload** or **documented restart**)

## Tasks / subtasks

- [x] **Dependencies & config (AC: 1)** — Add a **maintained** scheduler/cron dependency via **`uv add`** (e.g. **APScheduler** 4.x or **croniter** + loop; justify choice in README). Extend **`Settings`** in **`pharma_rd/config.py`** with:
  - **`schedule_cron`**: string, **default = one run per week** (document the exact 5-field cron in README, e.g. weekly Sunday 00:00 UTC or another fixed weekly slot—must match “weekly default” in PRD).
  - Optional: **`scheduler_timezone`** if the library needs it (default **UTC** for reproducible demos).
  - Env: **`PHARMA_RD_SCHEDULE_CRON`**, etc., **`PHARMA_RD_`** prefix only.
  - **Validate** cron (or equivalent) at scheduler **startup**; exit **non-zero** with a **clear stderr message** if invalid (no stack trace in normal use).

- [x] **Scheduler runtime (AC: 1)** — Implement a **long-running “scheduler process”** entry path (new CLI subcommand, e.g. **`pharma-rd scheduler`** or **`pharma-rd schedule run`**—pick one, document it). The process must:
  - Parse cron (or equivalent) from **`get_settings()`**.
  - On each tick, invoke the **same execution path** as **`pharma-rd run`**: create **`run_id`**, **`connect(settings.db_path)`**, **`run_pipeline(...)`** — **reuse** **`run_foreground_pipeline`** logic by extracting a shared function (e.g. **`execute_scheduled_pipeline_run()`** in **`cli.py`** or **`pipeline/scheduler.py`**) so behavior matches foreground runs (artifacts, logs, DB).
  - **Do not** duplicate pipeline orchestration outside **`run_pipeline`**.

- [x] **Overlap / failure behavior (AC: 1, ops)** — If a scheduled tick fires while a previous run is still in progress, **skip** the new tick or **log and skip** (document one approach; avoid overlapping full pipelines on SQLite MVP). Scheduled failures must not crash the scheduler loop unless unrecoverable (log + continue).

- [x] **Config reload vs restart (AC: 1)** — Implement **one** of:
  - **Documented restart**: settings read at process start; changing **`.env` / env** requires restarting the scheduler process; document clearly in README, **or**
  - **Lightweight reload**: e.g. **`SIGHUP`** or periodic re-read of env (only if small and tested).
  - State which option was implemented in README and in this story’s Completion Notes.

- [x] **Docs** — **`README.md`**: how to run the scheduler, default weekly cron, env vars, overlap policy, restart/reload behavior, and how this relates to **`pharma-rd run`** (on-demand).

- [x] **Tests** — **`tests/test_scheduler.py`** (or similar): unit tests for cron parsing / “next run” wiring with **fakes or short interval** (no 7-day waits); assert **`run_pipeline`** (or shared runner) is invoked when a job fires (mock **`run_pipeline`**). **`ruff`** + **`pytest`** green in CI.

### Review Findings

- [x] [Review][Patch] Default cron **`0 0 * * 0`** was documented as **Sunday** 00:00, but **APScheduler** `CronTrigger.from_crontab` maps numeric **`0` in DOW to Monday** — **mismatch** with README/PRD weekly-Sunday intent. — **Fixed:** default **`0 0 * * sun`**, README note, **`.env.example`**, **`Settings`** description, test env.

## Dev notes

### Epic context (Epic 2)

[Source: `_bmad-output/planning-artifacts/epics.md` — Epic 2]

Epic 2 adds **recurring schedules**, **stage timeouts/retries** (2.2), and **stage retry without redoing upstream** (2.3). **This story is only 2.1** — do **not** implement bounded HTTP retries, per-stage timeouts, or partial stage retry graphs here.

### Scope boundaries

| In scope (2.1) | Out of scope (later stories) |
|----------------|--------------------------------|
| Configurable cron (or equivalent), weekly default, scheduler process | **2.2** HTTP timeouts/retries, **2.3** retry failed stage only |
| Trigger full pipeline via existing **`run_pipeline`** | New HTTP APIs unless trivially needed for health (prefer none) |
| Overlap skip/log policy | Distributed workers, multi-node locks |

### Architecture compliance

| Topic | Requirement |
|-------|-------------|
| **Scheduling decision** | [Source: `architecture.md` — “Scheduling: In-process scheduler vs OS cron vs external worker”] — **in-process** scheduler aligned with MVP is acceptable; document tradeoff. |
| **Config** | [Source: `architecture.md` — pydantic-settings, env] — all new settings via **`Settings`** + **`PHARMA_RD_`** prefix. |
| **Logging** | Reuse existing structured logging from **`run_pipeline`** / **`logging_setup`**; scheduled runs use same **`run_id`** as correlation. |
| **Persistence** | SQLite + **`RunRepository`** unchanged except as needed for future stories; no schema change **required** for 2.1 unless you add a **`scheduler_runs`** audit table (optional; not required by AC). |
| **JSON / naming** | **`snake_case`** for any new config fields or CLI JSON. |

### Technical requirements

1. **Reuse** **`pharma_rd.cli.run_foreground_pipeline`** core: extract inner function that returns exit code and optionally suppresses summary line for scheduler (or always log summary to structured log only—**document** stdout behavior: foreground **`pharma-rd run`** keeps last-line JSON; scheduler may log to structured logs only to avoid duplicating operator JSON on stdout every week).

2. **Stdout policy**: On-demand **`pharma-rd run`** keeps current behavior (last line JSON). **Scheduler-driven** runs should **not** spam operator JSON lines on stdout every tick unless documented; prefer **structured logs only** for scheduled executions, or one line per run—**pick one** and document.

3. **Time**: Use **UTC** for cron interpretation unless **`scheduler_timezone`** is set; document demo impact.

### Project structure notes

- Prefer new module: **`pharma_rd/scheduler.py`** or **`pharma_rd/pipeline/scheduler.py`** for APScheduler wiring; **thin** — orchestration stays in **`run_pipeline`**.
- Wire CLI in **`pharma_rd/main.py`** next to existing subcommands.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.1]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR2]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Scheduling, config, logging]

## Previous story intelligence

- **1.6** established **`pharma-rd runs` / `status`**, **`operator_queries`**, and **`pipeline/order.py`** — do not import heavy **`runner`** from read-only paths; scheduler should call **`run_pipeline`** directly like **`cli.run_foreground_pipeline`**.
- **1.5** **`run_foreground_pipeline`**: create run + **`run_pipeline`** — **refactor for reuse** rather than copy-paste.
- **1.4** structured logs: scheduled runs remain observable via same log stream fields (**`run_id`**, **`correlation_id`**).

## Git intelligence

- Follow **`ruff`** + **`pytest`** CI; add dependency in **`pyproject.toml`** / **`uv.lock`** via **`uv add`**.

## Latest technical notes

- **APScheduler** 4.x: cron-style triggers, well-supported on Python 3.12; alternatively **croniter** + sleep loop—keep dependency minimal and justified.
- Do **not** pin unrelated major upgrades beyond the scheduler stack in this story.

## Project context reference

- No **`project-context.md`** in repo root **`docs/`**; rely on this story + **`architecture.md`**.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

### Completion Notes List

- **APScheduler 3.11.2** (stable; v4 not GA on PyPI) via **`uv add apscheduler`** — **`CronTrigger.from_crontab`**, **`BlockingScheduler`**.
- **`execute_pipeline_run(emit_summary_json=...)`** in **`cli.py`**; scheduled path uses **`False`** (no summary JSON line on stdout).
- **`pharma_rd/scheduler.py`**: overlap skip via **`threading.Lock.acquire(blocking=False)`** + structured log **`scheduler_skip`**.
- **Config reload:** **documented process restart** only (no SIGHUP reload).
- **`Settings`**: **`schedule_cron`**, **`scheduler_timezone`** (IANA validated); invalid cron fails at **`pharma-rd scheduler`** startup.
- Code review: default cron DOW corrected to **`sun`** (APScheduler DOW `0` = Monday); **`pytest`** / **`ruff`** green after fix.

### Implementation Plan

Config → shared execute → scheduler module → **`pharma-rd scheduler`** → tests → README / `.env.example`.

### File List

- `pharma_rd/pyproject.toml`
- `pharma_rd/uv.lock`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/cli.py`
- `pharma_rd/pharma_rd/main.py`
- `pharma_rd/pharma_rd/scheduler.py` (new)
- `pharma_rd/tests/test_scheduler.py` (new)
- `pharma_rd/tests/test_smoke.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change log

- 2026-04-04: Story created — ultimate context engine analysis completed; status **ready-for-dev**.
- 2026-04-04: Implemented — APScheduler cron, **`pharma-rd scheduler`**, **`execute_pipeline_run`**, tests, README; status **review**.
- 2026-04-04: Code review — fixed APScheduler DOW documentation/default (**`sun`**); status **done**.
