# Story 1.5: On-demand pipeline run trigger

Status: done

## Story

As a **workflow operator**,
I want **to start a full pipeline run on demand**,
so that **I can demo or test without waiting for a schedule** (FR1).

## Acceptance criteria

1. **Given** valid configuration (stub sources acceptable)
   **When** the operator invokes the documented trigger (**CLI** command; **REST** optional in a later increment unless explicitly added here)
   **Then** a new **`run_id`** is created and the pipeline executes through stub or available stages.

2. **When** the run **completes successfully**
   **Then** the process prints a **machine-readable** result that includes **`run_id`** and a **`poll_status`** hint (stable **`snake_case`** JSON keys per architecture) so operators or scripts know how to observe status when **`GET /runs/{id}`** or **`pharma-rd status`** exists (story **1.6**).

3. **When** the run **fails** (exception from pipeline)
   **Then** the process exits **non-zero** and does **not** print a success summary line; errors are visible on **stderr** (message only — no secrets).

4. **Boundaries:** Wire **`connect`**, **`RunRepository.create_run`**, **`run_pipeline`** with **`get_settings()`** for DB path and artifact root. **Do not** implement **full** `GET /runs/{id}` (story **1.6**). **REST `POST /runs`** is **out of scope** unless timeboxed — **CLI** is the required deliverable for this story.

5. **Logging:** Structured JSON logs from **1.4** may share **stdout** with the CLI summary; the **final** line of stdout for a successful **`pharma-rd run`** is the **summary JSON** (operators can **`tail -1`** or parse lines for an object containing **`poll_status`**).

## Tasks / subtasks

- [x] **CLI** (AC: 1–3): Add **`pharma-rd run`** via **`argparse`** (stdlib). Entry: **`pharma_rd.main`** — subcommand **`run`** calls **`pharma_rd.cli.run_foreground_pipeline`**.

- [x] **Orchestration** (AC: 1–3): **`run_foreground_pipeline`**: **`connect(settings.db_path)`**, **`RunRepository().create_run(conn)`**, **`run_pipeline(..., artifact_root=settings.artifacts_root, run_id=...)`**, close connection; on success **`print`** one JSON line with **`run_id`**, **`poll_status`** (e.g. `GET /runs/{run_id}` placeholder for **1.6**).

- [x] **Default invocation** (AC: 1): **`pharma-rd`** with no subcommand prints **help** (document in README).

- [x] **Tests** (AC: 1–3): **`tests/test_cli.py`** — **`tmp_path`** DB + artifacts via env, **`get_settings.cache_clear()`**, invoke **`main_exit_code()`** or **`run_foreground_pipeline`** with **`monkeypatch.setattr(sys, "argv", ...)`**; assert exit code, **`run_id`** in DB, summary JSON parseable (last stdout line or line with **`poll_status`**).

- [x] **Docs**: **`README.md`** — **`pharma-rd run`**, env vars, summary line convention, pointer to **1.6** for status.

## Dev notes

### Epic context

Epic 1: **1.5** trigger → **1.6** operator visibility. [Source: `epics.md`]

**Implements:** **FR1**.

### Architecture compliance

| Topic | Requirement |
|-------|-------------|
| **REST paths** | Placeholder `GET /runs/{run_id}` in **`poll_status`** string aligns with `architecture.md` § API patterns |
| **JSON** | **`snake_case`** keys for summary object |
| **Config** | **`get_settings()`** only; **`PHARMA_RD_`** prefix |
| **Trigger** | Thin glue — **no** business logic in CLI beyond orchestration |

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 1.5]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR1]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Trigger / status API]

## Dev Agent Record

### Agent Model Used

Cursor Agent (Composer)

### Completion Notes List

- Added **`pharma_rd/cli.py`** with **`run_foreground_pipeline()`**; **`main.py`** uses **`argparse`** subcommand **`run`**.
- Success summary printed as **final** stdout line after structured logs; **`poll_status`** placeholder for **1.6**.
- **`tests/test_cli.py`**; **`uv run ruff check .`** and **`uv run pytest`** pass.

### File List

- `pharma_rd/pharma_rd/cli.py`
- `pharma_rd/pharma_rd/main.py`
- `pharma_rd/tests/test_cli.py`
- `pharma_rd/README.md`

## Change log

- 2026-04-04: Story implemented — CLI `pharma-rd run`, tests, README; status **done**.
