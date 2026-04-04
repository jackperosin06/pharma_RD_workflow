# Story 1.2: Persist runs and stages in SQLite

Status: done

<!-- Optional: run Validate Story ([VS]) before dev-story for a formal readiness check. -->

## Story

As a **workflow operator**,
I want **each pipeline run and stage recorded durably**,
so that **I can inspect what ran and what failed after the fact** (NFR-R2).

## Acceptance criteria

1. **Given** a configured SQLite database path and an explicit **schema version / migration** story (DDL applied on open or first use)
   **When** the application initializes persistence
   **Then** the database file exists (or is created), **schema version** is recorded, and tables support **runs** and **stages** as below.

2. **When** a **run** is created
   **Then** a row exists with **`run_id`** (opaque string; **UUID v4** preferred per architecture), **created_at** / **updated_at** (ISO 8601 UTC semantics), and **overall run `status`** (at minimum: values sufficient for later stories—e.g. `pending`, `running`, `completed`, `failed`; align names with `architecture.md` process patterns such as `partial_failed` when introduced).

3. **When** a **stage** is recorded for that run
   **Then** a **stage** row is **inserted or updated** (same logical stage keyed by **`run_id` + stage identifier**), linked to **`run_id`**, with **`status`** in **`pending`**, **`running`**, **`completed`**, or **`failed`**, and timestamps as appropriate (at minimum `updated_at`; `started_at` / `ended_at` if straightforward).

4. **Retention (NFR-R2):** Run history retention is **configurable** via settings; **default is 30 days** for practice. Implementation must include a **documented** mechanism to **purge or exclude** runs older than the retention window (e.g. delete query, or documented filter for future readers; a small callable used from tests is enough—full scheduler is **not** required in 1.2).

5. **Boundaries:** **No** full pipeline runner, **no** artifact file writes, **no** structured JSON logging requirement beyond what tests need—those are **1.3+**. Persistence **only** touches SQLite via **`pharma_rd/persistence/`** (architecture boundary).

## Tasks / subtasks

- [x] **Config** (AC: 1, 4): Extend `pharma_rd/config.py` / `.env.example` with **non-secret** settings, e.g. SQLite path (default under `data/` or equivalent), **retention days** (default **30**). Use **`PHARMA_RD_`** prefix; no ad hoc `os.environ` elsewhere. [Source: architecture § Implementation patterns; story 1.1]

- [x] **`persistence/` package** (AC: 1, 2, 3, 5): Add `pharma_rd/persistence/__init__.py`, `db.py` (connection, **migrate/init** schema, **schema version**), and a small API surface (functions or a repository class) to:
  - [x] Create a run (`run_id`, initial status).
  - [x] Upsert or update stage rows for `(run_id, stage)` with allowed statuses.
  - [x] Apply **versioned DDL** once per new version (e.g. `schema_version` table + incremental SQL strings, or a single `CURRENT_SCHEMA_VERSION` constant).

- [x] **Schema** (AC: 1–3): **`snake_case`** table/column names. [Source: architecture § Naming patterns]
  - [x] **`runs`**: `run_id` (PK), status, `created_at`, `updated_at`, plus any minimal fields needed for integrity.
  - [x] **`stages`**: FK to `run_id`, stage name/key, status, timestamps; unique constraint on `(run_id, stage)` if one row per stage.

- [x] **Retention** (AC: 4): Implement **`purge_runs_older_than(retention_days)`** (or equivalent) using configured default; callable from tests; document behavior in README snippet or module docstring.

- [x] **Tests** (AC: 1–4): **`tests/persistence/`** (or mirror structure) using **temporary SQLite files**; prove create run, stage transitions, schema idempotence, and retention purge removes old rows. No network; **ruff** + **pytest** in CI unchanged.

- [x] **Docs**: Short note in `pharma_rd/README.md`: DB path env, retention default, where schema lives.

## Dev notes

### Epic context (Epic 1)

Epic 1 delivers an **executable pipeline foundation**: scaffold (1.1 ✓), **durable run/stage state** (this story), runner + artifacts (1.3), logging (1.4), trigger (1.5), operator visibility (1.6). [Source: `_bmad-output/planning-artifacts/epics.md` § Epic 1]

**Implements:** FR4 (foundation), FR5 (run record foundation), architecture **data layer**.

### Scope boundaries (prevent creep)

| In scope (1.2) | Out of scope (later stories) |
|----------------|------------------------------|
| SQLite schema + migrations/version, runs/stages CRUD, config, retention helper | Ordered pipeline execution, Pydantic stage payloads, artifact files (1.3) |
| | Correlation ID / structured logging (1.4) |
| | CLI `trigger` / HTTP API (1.5) |
| | Rich operator UX / listing polish (1.6) |

### Architecture compliance

| Topic | Requirement |
|-------|---------------|
| **DB** | **SQLite**; stdlib **`sqlite3`** acceptable for MVP, or **SQLAlchemy 2.x** if you introduce an ORM—keep migrations explicit. [Source: `architecture.md` § Data architecture] |
| **Migrations** | **Schema version in DB** + incremental SQL; avoid silent incompatible changes. [Source: architecture § Data architecture — Migrations] |
| **Layout** | **`pharma_rd/persistence/`** — only this package talks to SQLite for app data; agents/pipeline do not embed SQL. [Source: architecture § Architectural boundaries — Persistence] |
| **Naming** | DB: **snake_case**; `run_id` opaque (**UUID** preferred). [Source: architecture § Naming patterns] |
| **Timestamps** | **ISO 8601 UTC** in API/logs; DB can store TEXT ISO or consistent integer—document choice. [Source: architecture § Format patterns] |
| **Config** | Single **settings** module; **extend** existing `get_settings()` / `Settings`. [Source: architecture § Enforcement guidelines] |
| **Repo root** | Python app stays under **`pharma_rd/`** next to `_bmad-output/`, not inside planning folders. [Source: story 1.1; architecture § Project structure] |

### Project structure notes

- Actual repo uses **flat** package layout `pharma_rd/pharma_rd/` (not `src/`). New modules go under **`pharma_rd/pharma_rd/persistence/`** to match installed package name.
- **`.gitignore`** already ignores `data/`, `*.db` where applicable—ensure default DB path remains gitignored.

### Library / dependency strategy

- Prefer **no new runtime dependencies** if **`sqlite3`** + hand-written SQL suffices.
- If you add **SQLAlchemy 2.x**, **`uv add`** it and pin in **`uv.lock`**; justify in dev notes.
- Do **not** add LangGraph, FastAPI, or schedulers for this story.

### Testing requirements

- **pytest** + **ruff** per `pyproject.toml`.
- Use **tmp_path** / temporary DB files; no real `data/` pollution in tests.
- Cover: migration runs twice without error, FK or consistency as designed, retention deletes or filters old runs.

### Latest technical notes (SQLite / Python 3.12)

- Use **`sqlite3.connect`** with `check_same_thread=False` only if you later share connections across threads; default single-threaded tests OK.
- Consider **`PRAGMA foreign_keys = ON`** after connect if using FKs.
- **UUID:** `uuid.uuid4()` string for `run_id`.

## Previous story intelligence

- **Story 1.1** established **`uv`**, **`pharma_rd/pharma_rd/`** package, **`config.py`** with **`PHARMA_RD_`** prefix, **`.env.example`**, **CI**, **`tests/test_smoke.py`**. Reuse patterns; extend settings rather than new env reads.
- **Review / defer:** `httpx` remains unused until HTTP work—do not remove. Console script vs **`python -m pharma_rd`** behavior on macOS was noted; rely on **module** entry for tests if needed.

## Git intelligence

- Treat **`pharma_rd/`** as the app root; commit **`uv.lock`** if new dependencies are added.

## Project context reference

- No **`project-context.md`** in repo; rely on this story + `architecture.md` + `prd.md` + `epics.md`.

## Dev Agent Record

### Agent model used

Cursor Agent (Composer)

### Debug log references

- None.

### Completion notes list

- Implemented stdlib-only SQLite persistence under `pharma_rd/persistence/`: `connect()` runs `PRAGMA foreign_keys = ON`, migrates via `PRAGMA user_version` (v1 DDL for `runs` / `stages`).
- `RunRepository` creates UUID `run_id`, validates run/stage status strings, upserts stages with `started_at` / `ended_at` when transitioning to running / terminal states.
- `purge_runs_older_than(conn, retention_days=...)` deletes old runs (CASCADE removes stages); settings expose `db_path` and `retention_days` for future callers.
- All tests pass: `ruff check .` and `pytest` (13 tests after review fixes).

### File list

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/persistence/__init__.py`
- `pharma_rd/pharma_rd/persistence/db.py`
- `pharma_rd/pharma_rd/persistence/repository.py`
- `pharma_rd/tests/persistence/test_persistence.py`
- `pharma_rd/.env.example`
- `pharma_rd/README.md`

## Change log

- 2026-04-04: Implemented story 1.2 — SQLite runs/stages schema, repository API, retention purge, config + docs + tests.
- 2026-04-04: Code review follow-up — stage retries (terminal → pending/running), duplicate `run_id` / empty `stage_key` validation, datetime-based retention purge, tests.

### Review Findings

- [x] [Review][Decision] Stage retry semantics — **Resolved (2026-04-04):** Retries allowed; `RunRepository.upsert_stage` resets timestamps when leaving terminal `completed`/`failed` (`pending` clears `started_at`/`ended_at`; `running` sets fresh `started_at`, clears `ended_at`).

- [x] [Review][Patch] Duplicate explicit `run_id` — **Resolved:** `create_run` catches `sqlite3.IntegrityError` and raises `ValueError("run_id already exists: …")`.

- [x] [Review][Patch] Empty `stage_key` — **Resolved:** `upsert_stage` rejects blank/whitespace-only keys with `ValueError`.

- [x] [Review][Patch] Purge ordering invariant — **Resolved:** `purge_runs_older_than` parses each `created_at` with `_parse_utc_iso` and compares UTC datetimes; malformed values raise `ValueError` with a clear message.

- [x] [Review][Defer] Index on `runs(created_at)` for retention scans at scale — optional optimization once row counts grow; not required for story 1.2. [`db.py:13-19`] — deferred, pre-existing / scale concern

---

**Story context:** Ultimate context engine analysis completed — comprehensive developer guide created for **`bmad-dev-story`** ([DS]).
