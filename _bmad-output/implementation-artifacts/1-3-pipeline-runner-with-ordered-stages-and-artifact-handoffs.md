# Story 1.3: Pipeline runner with ordered stages and artifact handoffs

Status: done

<!-- Optional: run Validate Story ([VS]) before dev-story for a formal readiness check. -->

## Story

As a **workflow operator**,
I want **stages to execute in the required order with persisted outputs between stages**,
so that **handoffs match the PRD pipeline model** (Clinical → Competitor → Consumer → Synthesis → Delivery).

## Acceptance criteria

1. **Given** a **run** exists (created via persistence; `run_id` opaque per architecture)
   **When** the **pipeline runner** executes for that run
   **Then** stages run **strictly in order**: **clinical** → **competitor** → **consumer** → **synthesis** → **delivery** (stage keys **snake_case**, aligned with PRD five-agent pipeline and `architecture.md` internal pipeline decision).

2. **When** each stage **completes successfully**
   **Then** its **structured output** is **Pydantic v2–validated**, **serialized to JSON**, written under the configured **artifact root**, and **metadata** (**path** relative to artifact root, **SHA-256** content hash) is **persisted in SQLite** so downstream stages and operators can locate the blob.

3. **When** a stage **starts** (after the first)
   **Then** it receives **inputs derived from upstream persisted artifacts** per the **pipeline contract** below (at minimum: each stage after clinical loads the **previous stage’s** validated output; **delivery** consumes **synthesis** output—document the exact wiring in code comments or a small `PIPELINE_EDGES` map so Epic 2+ retries do not guess).

4. **When** a stage **fails** (raises or returns a contract violation)
   **Then** the run’s overall status reflects failure (**`failed`** or **`partial_failed`** per existing `RunRepository` / run status vocabulary), the failing **stage** row is terminal **`failed`**, **downstream stages are not executed**, and **no silent partial success** is reported as full completion.

5. **Stub implementations** are **acceptable**: each agent module may return **minimal valid** payloads that satisfy the Pydantic models (e.g. empty lists, placeholder strings) until real agents exist in later epics—**no** external HTTP **required** in this story.

6. **Boundaries:** Implement **orchestration + artifact I/O + DB metadata** in this increment. **Do not** implement **structured JSON logging to stdout** as a product requirement here—that is **story 1.4**. **Do not** implement **CLI/HTTP trigger** as the primary operator entry—that is **story 1.5**; a **callable** `run_pipeline(...)` (or equivalent) invoked from **tests** and optionally wired from `main` later is enough.

## Tasks / subtasks

- [x] **Config** (AC: 2): Extend `pharma_rd/config.py` and `.env.example` with **`PHARMA_RD_ARTIFACTS_ROOT`** (or equivalent name) defaulting to a repo-relative **`artifacts/`** directory; **gitignored** by default (align with `.gitignore`). [Source: architecture § Artifact storage]

- [x] **Schema migration** (AC: 2): Bump **`CURRENT_SCHEMA_VERSION`** in `pharma_rd/persistence/db.py`; add DDL for **artifact metadata** (e.g. table `stage_artifacts` or columns on `stages`—prefer a dedicated table if you want one row per artifact with clear FK to `run_id` + `stage_key`). Store at least: **`relative_path`**, **`sha256_hex`**, **`byte_size`** (optional), **`created_at`**. Keep migrations **idempotent** and **forward-only** per story 1.2 pattern.

- [x] **Artifact store** (AC: 2): Implement write path in **`pharma_rd/persistence/`** only (architecture boundary: **only persistence** touches SQLite + artifact files for app data). Functions or a small class: **`write_stage_artifact(run_id, stage_key, model: BaseModel) -> metadata`** (hash file, insert row). Use **`pathlib`**, atomic write pattern (write temp + rename) if feasible; document Windows/macOS behavior if not.

- [x] **Pydantic contracts** (AC: 2, 3, 5): Add **`pharma_rd/pipeline/contracts.py`** (or `models/`) with **one output model per stage** (`ClinicalOutput`, `CompetitorOutput`, …) including a **`schema_version: int = 1`** field on each (architecture: version field on handoff models). **snake_case** JSON; round-trip tests.

- [x] **Stub agents** (AC: 5): Add **`pharma_rd/agents/`** package with **`clinical.py`**, **`competitor.py`**, **`consumer.py`**, **`synthesis.py`**, **`delivery.py`**—each exposes a **pure function or callable class** taking typed inputs + context (`run_id`, paths) and returning the **output model**. Stubs return **minimal valid** instances.

- [x] **Runner** (AC: 1–4): Add **`pharma_rd/pipeline/runner.py`** — orchestrates order, uses **`RunRepository`** + **`connect`** from existing persistence, updates **run** and **stage** rows (`pending` → `running` → `completed`/`failed`), loads previous artifact JSON into Pydantic for the next stage. **Single-threaded**, **in-process** per architecture.

- [x] **Tests** (AC: 1–5): **`tests/pipeline/`** — integration test with **`tmp_path`**: config artifact root under tmp, temp DB, create run, execute runner, assert stage order, files on disk, DB metadata, and failure short-circuit. **ruff** + **pytest** unchanged.

- [x] **Docs**: Extend **`pharma_rd/README.md`** — artifact root env, pipeline order, where contracts live.

## Dev notes

### Epic context (Epic 1)

Epic 1: scaffold (1.1 ✓), persistence (1.2 ✓), **this story** (runner + artifacts), then **1.4** logging, **1.5** trigger, **1.6** operator visibility. [Source: `epics.md` § Epic 1]

**Implements:** **FR3** (ordered stages + handoffs), **FR4** (persist intermediate outputs).

### Scope boundaries (prevent creep)

| In scope (1.3) | Out of scope (later stories) |
|----------------|------------------------------|
| Ordered runner, Pydantic JSON artifacts, SQLite metadata, stubs | **Correlation ID** / **structured JSON logs** to stdout (1.4) |
| | CLI `trigger` / **POST /runs** (1.5) |
| | **Per-stage timeouts/retries** (Epic 2) |
| | Real agent behavior / external APIs (Epic 3+) |

### Architecture compliance

| Topic | Requirement |
|-------|-------------|
| **Pipeline order** | **Clinical → Competitor → Consumer → Synthesis → Delivery** [Source: `architecture.md` § Internal pipeline; `prd.md` FR3] |
| **Handoffs** | **Pydantic** per stage; **persisted JSON** + DB metadata [Source: architecture § Validation; § Internal pipeline] |
| **Boundaries** | **Persistence** owns SQLite + artifact files; **agents** return data objects, **no** raw SQL in agent modules [Source: architecture § Architectural boundaries] |
| **Naming** | **snake_case** JSON and Python; stage keys match table/column style [Source: architecture § Naming patterns] |
| **Config** | **`get_settings()`** only; **`PHARMA_RD_`** prefix [Source: architecture § Enforcement guidelines] |
| **Layout** | Use **`pharma_rd/pharma_rd/pipeline/`**, **`pharma_rd/pharma_rd/agents/`** under the **existing flat layout** (`pharma_rd/pharma_rd/…`), not the architecture doc’s optional `src/` sketch—**do not** relocate the whole package in this story. |

### Pipeline contract (developer guardrails)

- **Stage keys (fixed order):** `clinical`, `competitor`, `consumer`, `synthesis`, `delivery`.
- **Default handoff wiring for MVP:** `competitor` consumes **`ClinicalOutput`** (from file); `consumer` consumes **`CompetitorOutput`**; `synthesis` consumes **`ConsumerOutput`**; `delivery` consumes **`SynthesisOutput`**. (Linear chain; adjust only if PRD requires fan-in—epics text implies sequential handoffs.)
- **File naming:** e.g. `{artifacts_root}/{run_id}/{stage_key}/output.json` — **document** the convention in README + module docstring so 1.5/1.6 stay consistent.
- **Run status:** Align with existing **`RUN_STATUSES`** in `RunRepository`; set run to **`completed`** only if **delivery** completes; use **`failed`** or **`partial_failed`** on stage failure per architecture partial failure pattern.

### Previous story intelligence (1.2)

- Reuse **`connect`**, **`RunRepository`**, **`purge_runs_older_than`** from `pharma_rd.persistence`; **extend** schema via **versioned migration**—do **not** fork a second DB API.
- **Retry semantics** for stages exist in **`RunRepository.upsert_stage`** (terminal → non-terminal); runner should still treat a **fresh run** linearly; **Epic 2** owns operator-driven **retry** of failed stages.
- **`httpx`** may remain unused until HTTP integrations—do **not** remove.
- Tests: **tmp_path**, no network; match **1.2** pytest style.

### Project structure notes

- **`.gitignore`:** Ensure **`artifacts/`** (or chosen default) is ignored; **`data/*.db`** already ignored.
- **`uv.lock`:** Run **`uv add`** only if you add a new dependency; **prefer stdlib + existing pydantic** for this story.

### Testing requirements

- **pytest** + **ruff** per `pyproject.toml`; mirror **`tests/pipeline/`** for new code.
- Prove: **happy path** all five stages; **failure** in stage 2 skips 3–5; **artifact file** exists and **hash** in DB matches file bytes.

### Latest technical notes

- **Pydantic v2** already required by project; use **`model_dump_json`** / **`model_validate_json`** for I/O.
- **SHA-256:** **`hashlib.sha256`** from stdlib.

## Previous story intelligence

- **Story 1.2** delivered SQLite **`runs`/`stages`**, **`RunRepository`**, **`purge_runs_older_than`**, **`PHARMA_RD_DB_PATH`**, **`PHARMA_RD_RETENTION_DAYS`**. Extend **`db.py`** migrations for artifact metadata—**do not** break existing tests; keep **1.2** tests green.

## Git intelligence

- Commit **`pharma_rd/`** changes and **`uv.lock`** if dependencies change; planning artifacts under **`_bmad-output/`** per team workflow.

## Project context reference

- No **`project-context.md`** in repo; use this story + **`architecture.md`** + **`prd.md`** + **`epics.md`**.

## Dev Agent Record

### Agent model used

Cursor Agent (Composer)

### Debug log references

- None.

### Completion notes list

- Added **`PHARMA_RD_ARTIFACTS_ROOT`** / `artifacts_root` settings; schema **v2** with **`stage_artifacts`** table (FK to `runs`, CASCADE delete).
- Implemented **`write_stage_artifact`**, **`read_artifact_bytes`**, **`artifact_relative_path`** in `persistence/artifacts.py` (temp file + rename).
- Added **`pipeline/contracts.py`** (five output models + `schema_version`), **`pipeline/runner.py`** with **`PIPELINE_ORDER`**, **`PIPELINE_EDGES`**, **`run_pipeline`**.
- Stub agents under **`pharma_rd/agents/`**; tests in **`tests/pipeline/`** (happy path, competitor failure → `partial_failed`, contract round-trips, artifact metadata).
- **`uv run ruff check .`** and **`uv run pytest`** — 17 tests passed.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/.env.example`
- `pharma_rd/README.md`
- `pharma_rd/pharma_rd/persistence/db.py`
- `pharma_rd/pharma_rd/persistence/artifacts.py`
- `pharma_rd/pharma_rd/persistence/__init__.py`
- `pharma_rd/pharma_rd/pipeline/__init__.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/agents/__init__.py`
- `pharma_rd/pharma_rd/agents/clinical.py`
- `pharma_rd/pharma_rd/agents/competitor.py`
- `pharma_rd/pharma_rd/agents/consumer.py`
- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_runner.py`

## Change log

- 2026-04-05: Implemented story 1.3 — pipeline runner, stage artifacts table, stub agents, integration tests.
- 2026-04-05: Code review — failure-path exception chaining (`runner.py`), artifact file rollback if DB insert fails (`artifacts.py`).

### Review Findings

- [x] [Review][Patch] `run_pipeline` failure path — preserve original exception when cleanup (`upsert_stage` / `update_run_status`) fails; use nested `try`/`except` with `raise cleanup_err from e`. [`runner.py:145-156`] — fixed during review.

- [x] [Review][Patch] `write_stage_artifact` — if SQLite insert fails after `output.json` is written, remove the file to avoid orphan blobs without metadata. [`artifacts.py:63-78`] — fixed during review.

- [x] [Review][Defer] Runner is intentionally repetitive (five explicit blocks) for readability; refactor to a data-driven loop is optional follow-up, not required for AC.

---

**Story context:** Ultimate context engine analysis completed — comprehensive developer guide created for **`bmad-dev-story`** ([DS]).
