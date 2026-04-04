# Story 2.3: Retry failed stage without re-running completed upstream

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **to retry only a failed stage** when supported,
so that **I do not manually recreate upstream artifacts** (FR30, NFR-R3).

## Acceptance Criteria

1. **Given** a run where upstream stages **completed** and a downstream stage **failed**
   **When** the operator invokes **stage retry**
   **Then** the system re-executes **only** the failed stage **and any downstream stages that have not yet completed successfully** (linear pipeline: after a failure, later stages are absent or incomplete—resume from the failed stage through the rest of the ordered graph)
   **And** execution uses **persisted upstream artifacts** on disk for handoffs (no re-run of completed upstream stages)

2. **And** artifact versioning or run metadata prevents **silent overwrites** (NFR-R3): retries must be **observable**—at minimum structured logs when a stage output is replaced, and **`stage_artifacts`** metadata reflects the new SHA-256 / timestamp after `write_stage_artifact` (existing `INSERT OR REPLACE` is acceptable if logs document the replacement clearly)

## Tasks / Subtasks

- [x] **Preconditions & validation (AC: 1, 2)** — Implement validation helpers (e.g. in `pharma_rd/pipeline/` or `operator_queries.py`) that, for a `(run_id, stage_key)`:
  - Confirm the **run** exists and is in a **retryable** state (`failed` or `partial_failed`, **not** `completed`).
  - Confirm **all upstream** stages in `PIPELINE_ORDER` before `stage_key` are **`completed`** in SQLite **and** `output.json` exists under `{artifacts_root}/{run_id}/{upstream}/`.
  - Confirm **`stage_key`** is **`failed`** (or define and document if “first incomplete” is allowed—default: **only explicit failed stage** for MVP clarity).
  - On violation: clear **stderr** message, **non-zero** exit, **no** partial DB mutation.

- [x] **Resume runner (AC: 1)** — Add **`run_pipeline_resume_from`** (name negotiable) in **`pharma_rd/pipeline/runner.py`** (or thin module imported by it) that:
  - Takes `conn`, `artifact_root`, `run_id`, **`start_stage_key`**, `repo` (same pattern as `run_pipeline`).
  - Sets run to **`running`** (or appropriate transition) and executes stages from **`start_stage_key`** through **`PIPELINE_ORDER[-1]`**, reusing the **same** agent calls and **`read_artifact_bytes` / `write_stage_artifact`** handoffs as the full runner.
  - **Does not** re-execute stages **before** `start_stage_key`.
  - On success through delivery: set run **`completed`**; on failure: same semantics as today (**`failed`** / **`partial_failed`**, **`error_summary`** on failing stage).
  - Reuse **`stage_logging`** / **`pipeline_run_logging`** and existing structured **`event`** names where possible; add **`stage_retry`** / **`pipeline_resume`** (or similar) events for operator demos.

- [x] **CLI entry (AC: 1)** — New subcommand, e.g. **`pharma-rd retry-stage <run_id> <stage_key>`** in **`pharma_rd/main.py`** + **`cli.py`**:
  - Wire **`connect(get_settings().db_path)`**, validate args against **`PIPELINE_ORDER`** (reject unknown `stage_key`).
  - Call **`run_pipeline_resume_from`**; stdout behavior: either **one summary JSON line** (aligned with **`pharma-rd run`**) or **document** “structured logs only”—pick one and match **`README.md`**.
  - Exit **0** on full success; **non-zero** on validation or pipeline failure.

- [x] **Overwrite transparency (AC: 2)** — Before overwriting a stage artifact on retry, **read prior `sha256_hex` from `stage_artifacts`** (if present) and emit a structured log line when the new digest **differs** after retry (fields: `run_id`, `stage`, `previous_sha256`, `new_sha256` or equivalent—**no** raw JSON bodies).

- [x] **Tests (AC: 1, 2)** — **`tests/pipeline/test_runner_resume.py`** (or extend **`test_runner.py`**):
  - **Failure injection** (e.g. `monkeypatch` on one agent) → **`partial_failed`** run → **`retry-stage`** on failed stage → assert **upstream** stage rows unchanged counts / still **completed**, **downstream** eventually **completed** when fix applied.
  - Assert **rejected** cases: unknown stage, **`completed`** run, retry when upstream incomplete.
  - Optional: cap **`error_summary`** length unchanged (repository already truncates).

- [x] **Docs** — **`README.md`**: operator-facing description, examples, relationship to **`pharma-rd status`**, and **`.env.example`** if any new env (avoid unless needed).

### Review Findings

- [x] [Review][Patch] **`run_pipeline_resume_from`**: validate **`start_stage_key`** is in **`PIPELINE_ORDER`** before **`PIPELINE_ORDER.index`** so direct library callers get a clear **`ValueError`** (opaque **`tuple.index`** errors) [`pharma_rd/pipeline/runner.py` ~246] — **fixed:** explicit **`unknown start_stage_key`** guard + test

## Dev Notes

### Epic context (Epic 2)

[Source: `_bmad-output/planning-artifacts/epics.md` — Epic 2, Story 2.3]

- **FR30** / **NFR-R3**: Retry without manual upstream recreation; **no silent conflicting artifacts** without clear versioning—address via logs + DB metadata as in AC2.
- **Prerequisite stories:** **2.1** scheduler and **2.2** HTTP retries are **orthogonal**; this story **must not** remove **`run_pipeline`** full-run behavior used by **`pharma-rd run`** and **`scheduler`**.

### Scope boundaries

| In scope | Out of scope |
|----------|----------------|
| Linear resume using existing **`PIPELINE_ORDER`** / **`PIPELINE_EDGES`** | DAG branching beyond the fixed order |
| CLI trigger for operators | New REST API unless trivially mirroring CLI (prefer **CLI only** for MVP) |
| SQLite + on-disk artifacts as today | Multi-writer / distributed locking |

### Architecture compliance

[Source: `_bmad-output/planning-artifacts/architecture.md`]

| Topic | Requirement |
|-------|-------------|
| **Orchestration** | In-process stages; **clear boundaries**; failure isolation (FR30) |
| **Partial failure** | Persist completed stages; **`partial_failed`** run (already implemented) |
| **Retries** | **Idempotent** inputs where possible; **log final** failure with `run_id` |
| **Observability** | Structured JSON logs; **correlation** via existing **`run_id`** |

### Technical requirements

1. **Reuse** `RunRepository.upsert_stage` — it already supports transitions **from terminal `failed` → `running`** (`leaving_terminal` resets timestamps). Verify behavior matches resume semantics; add tests if gaps.

2. **Single implementation path for stage bodies** — Avoid duplicating the five stage blocks: prefer **one** internal loop or dispatch map keyed by `stage_key` that calls `clinical.run_clinical`, `competitor.run_competitor`, etc., so **`run_pipeline`** and **`run_pipeline_resume_from`** share logic (refactor **`run_pipeline`** to call a shared internal function if needed).

3. **Imports:** **`operator_queries`** / **`cli`** should remain safe to import without pulling **`runner`** heavy paths where possible (follow **1.6** pattern); new CLI may import **`runner`** from **`cli`** only.

4. **Ordering:** Import **`PIPELINE_ORDER`** from **`pharma_rd.pipeline.order`** (not hard-coded duplicate lists).

### Project structure notes

- **`pharma_rd/pipeline/runner.py`** — primary location for resume orchestration.
- **`pharma_rd/cli.py`** — `retry_stage` handler.
- **`pharma_rd/main.py`** — argparse subcommand.
- **`pharma_rd/persistence/repository.py`** — only change if a small query helper is needed (prefer local SQL in runner/cli validation if one-off).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.3]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR30, NFR-R3]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Internal pipeline, retries, partial failure]
- [Source: `pharma_rd/pipeline/order.py` — `PIPELINE_ORDER`, `PIPELINE_EDGES`]
- [Source: `pharma_rd/persistence/artifacts.py` — `write_stage_artifact`, `read_artifact_bytes`]
- [Source: `pharma_rd/persistence/repository.py` — `upsert_stage` terminal transitions]

## Previous story intelligence

[Source: `_bmad-output/implementation-artifacts/2-2-per-stage-timeouts-and-bounded-retries-for-external-calls.md`]

- **2.2** added **`ConnectorFailure`**, **`ensure_connector_probe`**, and structured **`integration_error_class`** on stage failure—resume path must preserve the same logging/DB **`error_summary`** behavior for failures during **`retry-stage`**.
- **`connector_probe_url`** optional: full runs and resume runs both call the same agent functions; **no** special case unless tests require it.

## Git intelligence

- Repo history is minimal (initial scaffold + app). Follow existing **`ruff`** + **`pytest`** conventions and **`uv`** workflow in **`pharma_rd/README.md`**.

## Latest technical notes

- **SQLite:** `stage_artifacts` **UNIQUE (`run_id`, `stage_key`)** — replacement on retry updates **`sha256_hex`** / **`created_at`** via existing **`INSERT OR REPLACE`** in **`write_stage_artifact`**; pair with explicit **log** for NFR-R3 transparency.
- **httpx** / **APScheduler**: no version bumps required for this story unless resume introduces new dependencies (should not).

## Project context reference

- No **`project-context.md`** in repo; rely on **`architecture.md`** and this file.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

### Completion Notes List

- **`pharma_rd/pipeline/resume_validation.py`**: **`validate_stage_retry`** (read-only).
- **`pharma_rd/pipeline/runner.py`**: Refactored **`_execute_stage`**, **`run_pipeline`**, **`run_pipeline_resume_from`**; **`_write_artifact_with_replacement_log`** + **`stage_artifact_replaced`**; **`pipeline_resume`** / **`stage_retry`**; failure uses **`prior_upstream_completed`** + **`completed_in_invocation`** for **`partial_failed`** vs **`failed`**.
- **`RunRepository.get_stage_artifact_sha256`**
- **`pharma_rd/cli.py`** / **`main.py`**: **`pharma-rd retry-stage`**; summary JSON includes **`resumed_from`**.
- **`JsonLineFormatter`**: **`previous_sha256`**, **`new_sha256`**, **`resumed_from_stage`**
- Tests: **`tests/pipeline/test_runner_resume.py`** + autouse clear of **`PHARMA_RD_CONNECTOR_PROBE_URL`** / settings cache; **`test_smoke`** help line.

### File List

- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/pipeline/resume_validation.py`
- `pharma_rd/pharma_rd/pipeline/__init__.py`
- `pharma_rd/pharma_rd/persistence/repository.py`
- `pharma_rd/pharma_rd/cli.py`
- `pharma_rd/pharma_rd/main.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/pipeline/test_runner_resume.py`
- `pharma_rd/tests/test_smoke.py`
- `pharma_rd/README.md`
- `_bmad-output/implementation-artifacts/2-3-retry-failed-stage-without-re-running-completed-upstream.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change log

- 2026-04-05: Ultimate context engine analysis completed — comprehensive developer guide created; status **ready-for-dev**.
- 2026-04-05: Implemented resume validation, **`run_pipeline_resume_from`**, **`retry-stage` CLI**, artifact replacement logs, tests, README; status **review**.
- 2026-04-05: Code review — Review Findings appended; status **in-progress** (open patch items).
- 2026-04-05: Code review patches applied (`start_stage_key` guard + test); status **done**.
