# Story 1.4: Correlation ID and structured logging

Status: done

<!-- Optional: run Validate Story ([VS]) before dev-story for a formal readiness check. -->

## Story

As a **workflow operator**,
I want **every log line tied to a run and stage with a consistent correlation identifier**,
so that **I can narrate a demo and debug failures** (NFR-O1, NFR-O2, FR5).

## Acceptance criteria

1. **Given** a run has started with **`run_id`** (opaque string, already created by persistence / caller)
   **When** **pipeline or agent code** emits logs during **`run_pipeline`**
   **Then** each log line written to **stdout** is a **single JSON object** (one object per line, no pretty-printed multi-line blobs) containing at least:
   - **`run_id`** — same value as the run row and artifact paths for that execution
   - **`correlation_id`** — **identical to `run_id`** for MVP (document in code/README; reserve for future external correlation if split later) [Source: `architecture.md` § Format patterns — Run identity]
   - **`stage`** — snake_case stage key when the event pertains to a stage (`clinical`, …, `delivery`), or a documented sentinel (e.g. `null` / omitted only for true run-level events **if** you define those explicitly)
   - **`agent`** — **same string as `stage`** for stub agents unless you introduce a distinct agent name; must be present when `stage` is set [Source: `architecture.md` § Infrastructure — Logging]
   - **`level`** — log level name (e.g. `INFO`, `ERROR`) as string
   - **`message`** — short human-readable description
   - **`timestamp`** — **ISO 8601 UTC** (e.g. `2026-04-04T12:00:00Z`) [Source: `architecture.md` § Format patterns]

2. **When** a **stage** **starts**, **completes successfully**, or **fails**
   **Then** logs include **start/end or outcome** suitable for **Loom-style narration** (NFR-O2): e.g. explicit **`event`** values such as `stage_started`, `stage_completed`, `stage_failed`, plus **`outcome`** where useful (`completed`, `failed`, or error class/message — **no secrets, no raw PHI** per NFR-S4).

3. **When** the **run** transitions (**running** → **`completed`** / **`failed`** / **`partial_failed`**)
   **Then** there is a **run-level** structured log (e.g. `event`: `run_completed` or `run_failed`) including **`run_id`**, **`correlation_id`**, final **run status**, and **`completed_stage_count`** or equivalent so operators see the story at a glance.

4. **Consistency:** **`run_id`** in logs **matches** SQLite **`runs.run_id`** and artifact path convention **`{artifact_root}/{run_id}/...`** for that execution — no duplicate correlation scheme.

5. **Boundaries:** Implement **structured logging + correlation** in this increment. **Do not** implement **CLI/HTTP trigger** as the product entry (story **1.5**). **Do not** build **operator status UI/REST** beyond what tests need (story **1.6**). **Do not** remove or weaken existing **1.2 / 1.3** behavior.

## Tasks / subtasks

- [x] **Logging module** (AC: 1–3): Add **`pharma_rd/logging_setup.py`** (or **`pharma_rd/observability/`** package with a single public setup + logger facade — **pick one layout**, keep imports simple). Configure **structured JSON to stdout**: either **stdlib `logging`** with a **custom `Formatter`** emitting one JSON object per line, **or** add **`structlog`** with JSON output — **document the choice** in `README.md`. **Prefer** minimizing new dependencies unless `structlog` clearly reduces complexity; align with `architecture.md` (“structlog or stdlib”).

- [x] **Correlation & context** (AC: 1, 4): Ensure **`correlation_id`** is set from **`run_id`** at run start. Use **`contextvars`** and/or **logger adapters** so **`run_pipeline`**, **agents**, and persistence-adjacent code can emit logs **without** duplicating field names — **snake_case** keys everywhere [Source: `architecture.md` § Naming patterns].

- [x] **Runner instrumentation** (AC: 1–3): Update **`pharma_rd/pipeline/runner.py`** — log **run start**, each **stage** start/success/failure, and **run terminal** state, reusing the shared logging API. **Do not** log full artifact contents or secrets.

- [x] **Agent instrumentation** (AC: 1–2): Update **`pharma_rd/agents/*.py`** stubs to emit at least one **stage-scoped** log per invocation (e.g. “stub executed”) so logs prove **per-stage** correlation in tests — keep messages minimal.

- [x] **Initialization** (AC: 1): Call logging setup from **`run_pipeline`** entry (or a **single** module-level init guarded against double-configure) so **`uv run pytest`** and future CLI both get JSON logs without extra operator steps.

- [x] **Tests** (AC: 1–4): Add **`tests/`** coverage (e.g. **`tests/observability/`** or **`tests/pipeline/test_logging.py`**) — run **`run_pipeline`** in **`tmp_path`**, **capture stdout**, **parse each line as JSON**, assert required keys and **`correlation_id == run_id`**. Include a **failure** path asserting **`stage_failed`** / **`run_failed`** or equivalent appears.

- [x] **Docs**: Extend **`pharma_rd/README.md`** — log field dictionary, stdout JSON contract, **no secrets in logs**, correlation equals `run_id` for MVP.

## Dev notes

### Epic context (Epic 1)

Epic 1: **1.1 ✓**, **1.2 ✓**, **1.3 ✓** (runner + artifacts), **this story** (logging), then **1.5** trigger, **1.6** operator visibility. [Source: `epics.md` § Epic 1]

**Implements:** **FR5** (traceability / single-run correlation), **NFR-O1**, **NFR-O2**.

### Scope boundaries (prevent creep)

| In scope (1.4) | Out of scope (later stories) |
|----------------|------------------------------|
| JSON logs to **stdout**, **`run_id` + `correlation_id` + `stage` + outcome** | **CLI** `trigger` / **POST /runs** (**1.5**) |
| Runner + stub agent logs | **Rich operator dashboards**, **GET /runs** (**1.6**) |
| Demo-friendly narration fields | **Metrics backends**, OpenTelemetry export (future) |
| | **Stage timeouts/retries** (Epic 2) |

### Architecture compliance

| Topic | Requirement |
|-------|-------------|
| **Log destination** | **Structured JSON to stdout** [Source: `architecture.md` § Infrastructure — Logging] |
| **Fields** | **`run_id`**, **`correlation_id`**, **`stage`**, **`agent`**, level, message [Source: `architecture.md` § Infrastructure — Logging] |
| **Timestamps** | **ISO 8601 UTC** [Source: `architecture.md` § Format patterns] |
| **Naming** | **snake_case** for JSON keys [Source: `architecture.md` § Naming patterns] |
| **Enforcement** | “Include **`run_id`** (and **`stage`** when applicable) on **every** log line in pipeline code” [Source: `architecture.md` § Enforcement guidelines] |
| **Config** | **`get_settings()`** for any log-related config (e.g. log level env); **`PHARMA_RD_`** prefix for new env vars [Source: `architecture.md` § Enforcement guidelines] |
| **Layout** | Keep **`pharma_rd/pharma_rd/`** flat package layout from **1.1–1.3** — add `logging_setup.py` alongside `pipeline/`, `agents/`, not a wholesale move to `src/` [Source: story 1.3 § Architecture compliance] |

### Previous story intelligence (1.3)

- **`run_pipeline(conn, artifact_root=..., run_id=..., repo=...)`** is the central orchestration hook — **instrument here first**, then agents.
- **Artifact paths** use **`run_id`** as directory segment — logs must use the **same** `run_id` string.
- **Review fixes to keep:** failure paths preserve exception chaining; artifact file rollback if DB insert fails — **do not regress** when adding logging in `except` blocks.
- **Tests:** **`tmp_path`**, **no network**; follow **`tests/pipeline/`** style.

### Implementation hints (non-prescriptive)

- **Pattern:** `logging.Logger` with **`extra={...}`** + JSON **`Formatter`**, or **structlog** `bind(run_id=..., stage=...)`.
- **Run-level vs stage-level:** Use explicit **`event`** so grep/jq filters work for demos.
- **Security:** Never log **tokens**, **`.env` values**, or **PII/PHI**; stub agents should not log user content.

### Project structure notes

- New files likely under **`pharma_rd/pharma_rd/logging_setup.py`** (and optionally **`pharma_rd/pharma_rd/observability/`** if you split helpers).
- **`pyproject.toml`:** bump only if you add **`structlog`** (run **`uv add`** and commit **`uv.lock`**).

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 1.4]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR5, FR31, NFR-O1, NFR-O2, NFR-S4]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — § Infrastructure — Logging, § Format patterns, § Enforcement guidelines, § Pattern examples]

## Previous story intelligence

- **Story 1.3** delivered **`PIPELINE_ORDER`**, **`PIPELINE_EDGES`**, **`run_pipeline`**, **`write_stage_artifact`**, **`stage_artifacts`** table, stub **agents**, **`tests/pipeline/test_runner.py`**. Extend with logging **without** changing artifact contract or stage order.

## Git intelligence

- Recent commits center on **`pharma_rd/`** scaffold and BMad artifacts; follow existing **`ruff`** + **`pytest`** CI.

## Project context reference

- No committed **`project-context.md`** under **`docs/`**; rely on this story + **`architecture.md`** + **`prd.md`**.

## Latest technical notes

- **Python 3.12** + **stdlib `logging`** is sufficient for JSON lines; **`structlog`** 24.x is a common choice if you want bound loggers — either is acceptable if documented.

## Dev Agent Record

### Agent Model Used

Cursor Agent (Composer)

### Debug Log References

- None.

### Completion Notes List

- Implemented **`pharma_rd/logging_setup.py`**: **`contextvars`** for run/correlation/stage/agent, **`PipelineContextFilter`**, **`JsonLineFormatter`**, **`_StdoutJsonHandler`** (writes to **`sys.stdout` on each emit** so pytest capture and closed streams from prior tests do not break logging).
- **`configure_pipeline_logging()`** idempotent; called at start of **`run_pipeline`**.
- **`pipeline_run_logging`** / **`stage_logging`** context managers; runner logs **`run_started`**, **`stage_started`** / **`stage_completed`**, **`run_completed`**; failure path logs **`stage_failed`** (with **`error_type`**) and **`run_failed`** with **`completed_stage_count`** / **`run_status`**.
- Stub agents call **`log_agent_stub`** (`event`: **`agent_stub`**).
- **`PHARMA_RD_LOG_LEVEL`** in **`config.py`**; README + `.env.example` updated.
- Tests: **`tests/pipeline/test_logging.py`** — JSON parse + happy/failure paths; **`tests/test_config.py`** — `PHARMA_RD_LOG_LEVEL` validation; **`uv run ruff check .`** and **`uv run pytest`** — 21 tests passed after review patch.

### File List

- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/agents/clinical.py`
- `pharma_rd/pharma_rd/agents/competitor.py`
- `pharma_rd/pharma_rd/agents/consumer.py`
- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`

## Change log

- 2026-04-04: Story created — ultimate context engine analysis completed; status **ready-for-dev**.
- 2026-04-04: Implemented story 1.4 — structured JSON logging, correlation, tests, docs; status **review**.
- 2026-04-04: Code review — see Review Findings below.
- 2026-04-04: Code review patch — strict **`PHARMA_RD_LOG_LEVEL`** validation (`config.py`); story **done**.

### Review Findings

- [x] [Review][Patch] **Validate `PHARMA_RD_LOG_LEVEL`** — `configure_pipeline_logging()` uses `getattr(logging, level_name, logging.INFO)`, so unknown values (e.g. `FOO`) silently become INFO with no warning. Add a `pydantic` `field_validator` on `Settings.log_level` (or a fixed allow-list: DEBUG, INFO, WARNING, ERROR, CRITICAL) so misconfiguration fails fast or is logged once. [`pharma_rd/config.py`, `pharma_rd/logging_setup.py` ~97–99] — fixed: `field_validator` + `getattr(logging, settings.log_level)`; tests in `tests/test_config.py`.

- [x] [Review][Defer] **`run_started` vs DB order** — `run_started` is logged immediately before `repo.update_run_status(..., "running")`, so a reader correlating SQLite rows to stdout may see the narrative event slightly before the `runs` row shows `running`. Optional follow-up: emit `run_started` after the status update or document ordering. [`pharma_rd/pipeline/runner.py` ~68–72]

---
