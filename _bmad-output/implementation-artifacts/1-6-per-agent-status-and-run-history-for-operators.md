# Story 1.6: Per-agent status and run history for operators

Status: done

<!-- Optional: run Validate Story ([VS]) before dev-story for a formal readiness check. -->

## Story

As a **workflow operator**,
I want **to see per-agent (stage) status and historical runs**,
so that **I can verify execution for a recording and troubleshoot** (FR29, FR31).

## Acceptance criteria

1. **Given** at least one **completed** or **failed** run exists in SQLite
   **When** the operator uses the documented **`pharma-rd runs`** command (list recent runs)
   **Then** output includes **`run_id`**, overall **run `status`**, and **timestamps** (`created_at` / `updated_at` from `runs`) suitable for a **demo-friendly** view
   **And** listing supports **filtering to the last N runs** (e.g. **`--limit`**, default documented and sensible for demos, e.g. **20**).

2. **Given** a **`run_id`** exists
   **When** the operator uses **`pharma-rd status <run_id>`** (positional argument)
   **Then** output shows **per-stage** rows aligned with the pipeline (**`clinical` → … → `delivery`**) with **`stage_key`**, **`status`**, **`started_at`**, **`ended_at`** (from `stages`)
   **And** for **failed** stages, an **error summary** is shown when available (**NFR-R1** — not silent failure): either persisted in SQLite (see tasks) or a clear pointer to structured logs if persistence is deferred (pick one approach in implementation and document it).

3. **Consistency:** Field names in **JSON** output use **`snake_case`** [Source: `architecture.md` § Naming patterns]. Timestamps match stored **ISO 8601** strings from persistence.

4. **Boundaries:** **CLI** is the required deliverable (**FR29** / operator visibility). **`GET /runs/{id}`** HTTP handler is **optional** in this story — implement only if you can do so without blowing scope; otherwise document as **follow-up** next to **`poll_status`** from **1.5**. **Do not** implement **Epic 2** scheduling/retries here.

5. **Empty / missing data:** If **`runs`** is empty, **`pharma-rd runs`** exits **0** and prints an **empty list** (or documented message). If **`status`** is invoked for an unknown **`run_id`**, exit **non-zero** with a clear error on **stderr** (no stack trace in normal use).

## Tasks / subtasks

- [x] **Schema (AC: 2, NFR-R1)** (recommended): Bump **`CURRENT_SCHEMA_VERSION`** in **`pharma_rd/persistence/db.py`**; add nullable **`stages.error_summary`** (TEXT). Extend **`RunRepository.upsert_stage`** (or add **`set_stage_error_summary`**) to store a **short, safe** summary on terminal **`failed`** (truncate length, **no secrets**). Update **`pharma_rd/pipeline/runner.py`** failure path to pass **`error_type`** + brief **`str(e)`** (capped) into persistence when **`upsert_stage(..., "failed")`**.

- [x] **Read APIs** (AC: 1–2): Add query helpers (e.g. **`list_runs(conn, *, limit)`**, **`get_run_with_stages(conn, run_id)`**) in **`pharma_rd/persistence/`** or **`pharma_rd/operator_queries.py`** — **stdlib sqlite3** only; return **plain dicts** or small **dataclasses** for CLI serialization.

- [x] **CLI** (AC: 1–2, 5): Extend **`argparse`** in **`pharma_rd/main.py`** / **`pharma_rd/cli.py`**:
  - **`pharma-rd runs [--limit N]`** — print **one JSON object** to stdout (e.g. `{"runs": [...]}`) for scripting/Loom.
  - **`pharma-rd status RUN_ID`** — print **one JSON object** (e.g. `run`, `stages` array with **`error_summary`** nullable).

- [x] **Tests** (AC: 1–5): **`tests/test_operator_cli.py`** (or similar) — **`tmp_path`** DB, create run + stages via **`RunRepository`** / **`run_pipeline`** or direct SQL; assert JSON shape, **`--limit`**, unknown run exit code.

- [x] **Docs**: **`README.md`** — **`pharma-rd runs`**, **`pharma-rd status`**, **`--limit`**, example JSON, **error_summary** behavior.

### Review Findings

- [x] [Review][Patch] Move **`PIPELINE_ORDER`** (and optionally **`PIPELINE_EDGES`**) into a small module (e.g. `pharma_rd/pipeline/order.py`) and import it from **`runner`** and **`operator_queries`**. Today **`operator_queries`** does `from pharma_rd.pipeline.runner import PIPELINE_ORDER`, which executes **`runner.py`** and pulls in agents + logging for every **`pharma-rd runs` / `status`** invocation — unnecessary coupling and slower cold start. — `operator_queries.py:8` — **Done:** `pipeline/order.py`; **`operator_queries`** imports **`order`** only; **`pipeline/__init__`** re-exports **`PIPELINE_ORDER`** from **`order`**.
- [x] [Review][Patch] Stabilize **`list_runs`** ordering when **`created_at`** ties: use e.g. **`ORDER BY created_at DESC, run_id DESC`** so two runs inserted in the same clock tick are not ordered nondeterministically. — `operator_queries.py:17` — **Done.**

## Dev notes

### Epic context (Epic 1)

Epic 1 closes with **1.6** after **1.5** trigger. [Source: `epics.md` § Epic 1]

**Implements:** **FR29**, **FR31**; supports **NFR-R1** (failed stages visible with actionable summary).

### Scope boundaries (prevent creep)

| In scope (1.6) | Out of scope (later) |
|------------------|------------------------|
| CLI `runs` / `status`, SQLite reads | **HTTP server** for **`GET /runs/{id}`** (optional stub only) |
| **`error_summary`** on failed stage (if migrated) | Full **exception** stack / PII in DB |
| **Last N runs** | **Full-text search**, cross-tenant filters |
| | **Epic 2** retries, schedules |

### Architecture compliance

| Topic | Requirement |
|-------|-------------|
| **REST paths** | If you add HTTP, **GET** `/runs/{run_id}` [Source: `architecture.md` § API patterns] — **optional** |
| **JSON** | **`snake_case`** keys |
| **Persistence** | **Only** persistence layer touches SQLite for app data [Source: `architecture.md` § boundaries] |
| **Config** | **`get_settings()`** for DB path |

### Previous story intelligence (1.5)

- **`pharma-rd run`** creates **`run_id`** and runs **`run_pipeline`**; **`poll_status`** placeholder referenced **GET /runs/{id}`** — **1.6** fulfills operator **status** without requiring HTTP.
- **`main_exit_code()`** pattern — extend with new subcommands **`runs`** and **`status`**.

### Pipeline reference

- Stage order for display: **`PIPELINE_ORDER`** in **`pharma_rd/pipeline/runner.py`** — use same order when sorting stage rows for **`status`** output.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 1.6]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR29, FR31, NFR-R1]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Trigger/status API, naming]

## Previous story intelligence

- **1.5** added **`cli.py`**, **`main.py`** subcommand **`run`**, **`poll_status`** hint — extend CLI surface.
- **1.4** JSON logs — operator **status** JSON should **not** be confused with pipeline log lines; use **distinct** stdout for **`runs`** / **`status`** commands (or document if combined).

## Git intelligence

- Follow **`ruff`** + **`pytest`** CI; **forward-only** migrations per **1.2** / **1.3** pattern.

## Project context reference

- No **`project-context.md`** in **`docs/`**; use this story + **`architecture.md`**.

## Latest technical notes

- **SQLite** `json` module optional; **`json.dumps`** on dicts is enough for CLI.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

### Completion Notes List

- Schema v3: `stages.error_summary` (nullable TEXT); `upsert_stage(..., error_summary=...)` truncates to 512 chars; runner passes `{TypeName}: {message}` on stage failure.
- Operator read API: `pharma_rd/operator_queries.py` — `list_runs`, `get_run_with_stages` (stages sorted by `PIPELINE_ORDER`).
- CLI: `pharma-rd runs [--limit N]` (default 20), `pharma-rd status RUN_ID` — single JSON object stdout; unknown run exits 2 with stderr message.
- Full test suite green (`ruff`, `pytest`).
- Code review (2026-04-04): batch-applied patches — `pipeline/order.py` for **`PIPELINE_ORDER`** / **`PIPELINE_EDGES`**; **`list_runs`** tie-break **`run_id DESC`**.

### Implementation Plan

Red-green-refactor: migration + repository + runner error path; query module; CLI wiring; `test_operator_cli.py` + persistence/runner assertions; README.

### File List

- `pharma_rd/pharma_rd/persistence/db.py`
- `pharma_rd/pharma_rd/persistence/repository.py`
- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/pipeline/order.py`
- `pharma_rd/pharma_rd/operator_queries.py` (new)
- `pharma_rd/pharma_rd/cli.py`
- `pharma_rd/pharma_rd/main.py`
- `pharma_rd/tests/test_operator_cli.py` (new)
- `pharma_rd/tests/persistence/test_persistence.py`
- `pharma_rd/tests/pipeline/test_runner.py`
- `pharma_rd/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change log

- 2026-04-04: Story created — ultimate context engine analysis completed; status **ready-for-dev**.
- 2026-04-04: Implemented — schema v3, operator CLI `runs` / `status`, tests, README; status **review**.
- 2026-04-04: Code review patches applied (`order.py`, stable `list_runs` sort); status **done**.
