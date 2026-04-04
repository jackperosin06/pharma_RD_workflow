# pharma_rd (application)

Python package for the **pharma_RD** multi-agent pipeline. This directory is the **uv** project root (nested under the `pharma_RD_workflow` monorepo).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`, or `pip install uv`)

## Setup

From this directory (`pharma_rd/`):

```bash
uv sync --all-groups
```

Uses **Python 3.12** (see `.python-version`). The lockfile is `uv.lock`.

## Run

```bash
uv run pharma-rd --help
# or
uv run python -m pharma_rd --help
```

### On-demand pipeline run (FR1 / story 1.5)

Create a run, execute the full stub pipeline, then print a **summary JSON line** (after structured logs on stdout):

```bash
uv run pharma-rd run
```

- **Success:** exit code **0**. The **last** line of stdout is a JSON object: `run_id`, `poll_status` (placeholder `GET /runs/{run_id}` for a future HTTP API; use **`pharma-rd status <run_id>`** below for operator visibility without HTTP).
- **Failure:** exit code **non-zero**; error message on stderr.
- Uses **`PHARMA_RD_DB_PATH`** and **`PHARMA_RD_ARTIFACTS_ROOT`** like tests and `run_pipeline`.

### List runs & per-stage status (FR29 / FR31, story 1.6)

```bash
uv run pharma-rd runs
uv run pharma-rd runs --limit 50
uv run pharma-rd status <run_id>
```

- **`pharma-rd runs`:** prints **one JSON object** to stdout: `{"runs": [...]}`. Each run has **`run_id`**, **`status`**, **`created_at`**, **`updated_at`** (ISO 8601 strings from SQLite). Default **`--limit`** is **20** (newest runs first). If there are no runs, the list is empty and exit code is **0**.
- **`pharma-rd status RUN_ID`:** prints **one JSON object**: **`run`** (same fields as above) and **`stages`**, an array ordered **clinical → competitor → consumer → synthesis → delivery**. Each stage has **`stage_key`**, **`status`**, **`started_at`**, **`ended_at`**, **`error_summary`** (nullable). For **failed** stages, **`error_summary`** holds a short safe summary (exception type and message, capped); full stacks stay in structured logs, not in the DB.
- **Unknown `run_id`:** **`pharma-rd status`** exits **non-zero** and prints a clear message on stderr (no traceback in normal use).

Example **`runs`** output shape:

```json
{"runs":[{"run_id":"…","status":"completed","created_at":"…","updated_at":"…"}]}
```

Example **`status`** output shape:

```json
{"run":{"run_id":"…","status":"failed","created_at":"…","updated_at":"…"},"stages":[{"stage_key":"clinical","status":"completed","started_at":"…","ended_at":"…","error_summary":null},{"stage_key":"competitor","status":"failed","started_at":"…","ended_at":"…","error_summary":"RuntimeError: boom"}]}
```

### Retry a failed stage (FR30 / story 2.3)

When a run ends **`failed`** or **`partial_failed`** and a stage row is **`failed`**, you can **resume** from that stage using artifacts already written for upstream stages (no re-run of completed upstream work):

```bash
uv run pharma-rd retry-stage <run_id> <STAGE>
```

- **`STAGE`** is one of: **`clinical`**, **`competitor`**, **`consumer`**, **`synthesis`**, **`delivery`** (same order as **`pharma-rd status`**).
- **Preconditions:** the run is **not** **`completed`**; the target stage is **`failed`**; every **upstream** stage is **`completed`** and has **`output.json`** under the artifacts root. Otherwise the command exits **non-zero** with a short message on **stderr** (no traceback in normal use).
- **Success:** exit code **0**. The **last** line of stdout is JSON: **`run_id`**, **`poll_status`**, **`resumed_from`** (stage key). Structured logs include **`pipeline_resume`**, **`stage_retry`** per resumed stage, and **`stage_artifact_replaced`** when a stage output SHA-256 changes (NFR-R3).
- Use **`pharma-rd status <run_id>`** before/after to confirm stage rows and run status.

### Recurring schedule (FR2 / story 2.1)

Run a **long-lived in-process scheduler** (APScheduler **3.x**) that triggers the **same** full pipeline as **`pharma-rd run`** on a **cron** cadence:

```bash
uv run pharma-rd scheduler
```

- **Default cadence:** **`0 0 * * sun`** — minute/hour/day/month/day-of-week — **once per week**, **Sunday 00:00** in the configured timezone (PRD weekly default). **Note:** APScheduler’s `from_crontab` treats numeric **`0` in the DOW field as Monday**, not Sunday; use **`sun`** (or **`mon`**, etc.) for clarity.
- **Timezone:** `PHARMA_RD_SCHEDULER_TIMEZONE` (default **`UTC`**) — IANA name (e.g. `Europe/London`). Cron fields are interpreted in this zone.
- **Cron expression:** `PHARMA_RD_SCHEDULE_CRON` — standard **five-field** cron string. Invalid values cause **`pharma-rd scheduler`** to exit **non-zero** with a short message on **stderr** (no traceback in normal use).
- **Stdout:** Scheduled runs **do not** print the **`pharma-rd run`** summary JSON line on stdout; structured JSON logs from the pipeline still go to stdout (same as foreground runs).
- **Overlap:** If a tick fires while a run is still executing, the new tick is **skipped** and a **warning** is logged (`scheduler_skip`).
- **Config changes:** Restart the scheduler process after changing `.env` / environment (no hot reload in MVP). **`pharma-rd run`** and **`runs` / `status`** are unaffected by schedule settings.

## Lint & test (matches CI)

```bash
uv run ruff check .
uv run pytest
```

## Configuration

- Copy `.env.example` to `.env` for local overrides. Use **non-secret** keys only; real secrets stay out of git (NFR-S1).
- Settings use the `PHARMA_RD_` prefix (see `pharma_rd/config.py`).
- **Database:** `PHARMA_RD_DB_PATH` (default `data/app.db`) — SQLite file for run/stage history; parent directory is created on open. Schema DDL and version live in `pharma_rd/persistence/db.py` (`PRAGMA user_version`). **v2+** adds `stage_artifacts` (path + SHA-256 per stage output). **v3+** adds nullable **`stages.error_summary`** for short failed-stage messages (NFR-R1).
- **Artifacts:** `PHARMA_RD_ARTIFACTS_ROOT` (default **`artifacts/`** under cwd) — JSON blobs per run/stage at `{root}/{run_id}/{stage_key}/output.json`; metadata in `stage_artifacts`. Default folder is gitignored.
- **Retention:** `PHARMA_RD_RETENTION_DAYS` (default **30**) — use `purge_runs_older_than()` from `pharma_rd.persistence` to delete runs older than this window (cascades stages and artifact rows).
- **Pipeline:** Ordered stages **clinical → competitor → consumer → synthesis → delivery**; contracts in `pharma_rd/pipeline/contracts.py`, orchestration in `pharma_rd/pipeline/runner.py` (`run_pipeline`).
- **Structured logs:** `PHARMA_RD_LOG_LEVEL` (default **INFO**) — `configure_pipeline_logging()` runs at the start of `run_pipeline` and emits **one JSON object per line** to **stdout** (implementation: `pharma_rd/logging_setup.py`, stdlib `logging` only). **Correlation:** `correlation_id` equals `run_id` for MVP. Each line includes at least: `timestamp` (ISO 8601 UTC), `level`, `message`, `run_id`, `correlation_id`, `stage`, `agent`, `event`, `outcome` (and run-level fields such as `completed_stage_count` / `run_status` where applicable). **Do not** log secrets, tokens, or PHI/PII (NFR-S4).
- **Schedule (Epic 2):** `PHARMA_RD_SCHEDULE_CRON` (default **`0 0 * * sun`**, weekly Sunday) and `PHARMA_RD_SCHEDULER_TIMEZONE` (default **`UTC`**). Implementation: `pharma_rd/scheduler.py` (APScheduler). See **Recurring schedule** above.
- **Outbound HTTP (Epic 2 / story 2.2):** Shared **`httpx`** settings for connector calls: `PHARMA_RD_HTTP_TIMEOUT_SECONDS` (default **30**), `PHARMA_RD_HTTP_MAX_RETRIES` (default **3** extra attempts after the first request), `PHARMA_RD_HTTP_RETRY_BACKOFF_SECONDS` (default **0.5**, exponential backoff). Optional **`PHARMA_RD_CONNECTOR_PROBE_URL`**: when set, each pipeline stage performs a **GET** through this client before stub agent logic (leave unset for offline/tests). On failure, structured logs may include **`integration_error_class`** (e.g. `timeout`, `transient_exhausted`); stage **`error_summary`** in the DB includes the classification for operators.

## Layout note

The import package lives at `pharma_rd/pharma_rd/` (flat layout). This matches a normal editable install on all platforms; a future story may align folder names with the architecture doc’s `src/` sketch without changing import paths.

## CI

GitHub Actions workflow: `.github/workflows/ci.yml` at the **repository root** (not inside this folder). It sets `working-directory: pharma_rd` and runs `uv sync --all-groups --frozen`, `ruff check`, and `pytest`—same commands as above.
