---
stepsCompleted:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
  - 8
workflowType: architecture
lastStep: 8
status: complete
completedAt: '2026-04-04'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-pharma_RD_workflow.md
project_name: pharma_RD_workflow
user_name: Jackperosin_
date: '2026-04-04'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements overview

**Functional requirements (from PRD):** **35** FRs across **workflow orchestration** (FR1–FR5), **three monitoring agents** (Clinical FR6–FR7, Competitor FR8–FR10, Consumer FR11–FR13), **Synthesis** (FR14–FR17), **Delivery & consumption** (FR18–FR22), **configuration** (FR23–FR26), **transparency / quiet runs** (FR27–FR28), **operations & demo** (FR29–FR31), **access control** (FR32), plus **Phase 2–3** placeholders (FR33–FR35).

**Architectural reading:** The system is a **directed pipeline** with **persisted handoffs**, **correlation per run**, and **human-facing artifacts** (structured report)—not a single monolithic inference call.

**Non-functional requirements:** **Performance** (bounded run time for demo, timeouts/retries on external calls), **security & privacy** (secrets handling, TLS, no PHI in MVP by default), **reliability** (visible failures, durable run history, retry semantics), **integration** (graceful degradation, failure classification), **observability** (correlation ID, structured logs for Loom-style demos).

**Product brief alignment:** **iNova-style** pharma context; **human judgment** owns pursuit; **Delivery** only routes **insight artifacts**; **weekly-default** cadence with optional roll-ups; **practice** build vs **enterprise** hardening path.

**Epics / UX:** Not loaded—architecture will be driven primarily by **PRD FR/NFR** and **brief**; UI can stay thin (report viewer / email / file drop) unless a UX spec is added later.

### Scale & complexity

- **Primary domain:** **Backend workflow orchestration** + **LLM/agent steps** + **external data integrations** + **scheduled jobs**; minimal product surface for MVP.
- **Complexity level:** **High** — healthcare/pharma domain, evidence/citation expectations, future compliance path; **orchestration** and **integration** surface area dominate over raw user concurrency.
- **Indicative architectural components (logical):** **Scheduler/trigger**, **workflow runner** (DAG / ordered stages), **per-agent execution units** with **contracts**, **artifact store** (inter-stage + final report), **connector layer** for sources, **delivery adapter** (email/file/UI), **configuration service**, **observability** (logs, correlation).

### Technical constraints & dependencies

- **Practice MVP:** Public/mock feeds; **stub** internal research; **no** enterprise SSO required for FR26.
- **External dependency risk:** Third-party APIs and feeds (rate limits, schema drift)—NFR-I1/I2 and FR27–FR28 address **degradation** and **transparency**.
- **Regulatory positioning:** Decision-support / internal insight (per domain section)—not autonomous clinical action; shapes **audit** and **data** strategy for later phases.
- **Greenfield codebase:** No existing `project-context.md`; integration with live iNova systems is **out of scope** until explicitly added.

### Cross-cutting concerns

| Concern | Why it matters |
|--------|----------------|
| **Run correlation & traceability** | FR5, NFR-O1/O2 — demo and debugging |
| **Evidence / citations** | FR16, domain + innovation — trust and pharma norms |
| **Human-in-the-loop semantics** | FR22, brief — must not imply automated approval |
| **Failure isolation & retry** | FR30, NFR-P3/R1 — partial progress without silent failure |
| **Configuration vs code** | PRD + SaaS B2B section — TA scope, watchlists, schedule |
| **Future enterprise** | FR33–FR35, NFR-S4 — SSO, PHI, multi-tenant when productized |

## Starter Template Evaluation

### Primary technology domain

**Backend / workflow orchestration** with **LLM-backed agent steps**, **scheduled execution**, and **HTTP integrations**—not a mobile or rich SPA-first product. A thin **report delivery** surface (file/email/optional API) is enough for MVP.

### Starter options considered

| Option | Fit | Notes |
|--------|-----|--------|
| **`uv init` (Astral)** | **Recommended base** | Current, maintained; gives `pyproject.toml`, app layout, `.python-version`, fast `uv run` / `uv add`. See [uv project init](https://docs.astral.sh/uv/concepts/projects/init/). |
| **Cookiecutter FastAPI** | Defer / optional | Strong if you want **full web stack + auth + DB** immediately; heavier than PRD MVP (FRs focus on **pipeline + artifacts**, not a large product UI). |
| **Blank `git init` + manual** | Possible | Slower; no standard project metadata unless you add it. |

### Selected approach: **`uv` application project** (minimal scaffold)

**Rationale:** Establishes a **modern Python** baseline aligned with **LLM/agent libraries** and **incremental** addition of orchestration (e.g. LangGraph), HTTP clients, and schedulers **without** baking in unused subsystems.

**Initialization (run from parent of app root or adjust name):**

```bash
uv init pharma_rd
cd pharma_rd
```

Optional: pin a supported Python (LangGraph expects **Python ≥ 3.10**):

```bash
uv python pin 3.12
```

**First implementation stories (post-init):** add packages with `uv add` (e.g. `httpx`, `pydantic-settings`, orchestration/graph library, scheduler)—exact choices belong in implementation epics, not this scaffold.

**Architectural decisions implied by this starter**

- **Language & runtime:** Python (version pinned via `uv` / `.python-version`).
- **Packaging:** `pyproject.toml` + lockfile workflow via `uv`.
- **Styling / UI:** None from starter—add only if/when a real UI is in scope.
- **Testing / lint:** Add explicitly (e.g. `pytest`, `ruff`) in follow-on stories—`uv` supports them cleanly.

**Note:** Running the init command above should be tracked as an **early implementation story** once you start coding.

## Core Architectural Decisions

### Decision priority analysis

**Critical decisions (block implementation):**

- **Persistence model:** Where runs, steps, and artifact metadata live; how final reports are stored and retrieved.
- **Orchestration contract:** How the pipeline is invoked (CLI vs API), how long-running work is modeled, and how correlation IDs propagate.
- **Secrets and outbound HTTP:** How API keys and feed credentials are loaded and never logged (NFR-S*, FR27–FR28).

**Important decisions (shape the architecture):**

- **API surface:** Minimal REST (or RPC-style) for “trigger run / get status / fetch artifact” vs CLI-only for MVP.
- **Scheduling:** In-process scheduler vs OS `cron` vs external worker—must support weekly-default cadence (PRD).
- **Observability:** Structured logging format and correlation field names so Loom-style demos stay consistent.

**Deferred (post-MVP / Phase 2–3):**

- **Enterprise SSO, multi-tenant isolation, PHI-grade controls** (FR33–FR35, NFR-S4)—explicit roadmap only until productized.
- **Rich product UI** beyond report viewer / export—UX spec not loaded; keep thin.
- **GraphQL / event bus**—unnecessary for single-deploy MVP pipeline.

### Data architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Primary database** | **SQLite** (via Python **3.12+** standard library `sqlite3`, or **SQLAlchemy 2.x** + SQLite if an ORM is added) | Single-file, zero-ops for practice MVP; durable run history (FR5, NFR-R1); aligns with “greenfield / demo” scale. |
| **Artifact storage** | **Filesystem** under a configurable root (e.g. `artifacts/`), with **paths + hashes** in SQLite | Final structured report and intermediate agent outputs need files (PDF/HTML/JSON); avoids blob DB for MVP. |
| **Python runtime** | Pin **`3.12`** with `uv python pin 3.12` | **3.12** is supported through **Oct 2028** (security phase per [devguide](https://devguide.python.org/versions/)); **3.13+** acceptable later if all deps support it—pin explicitly in `.python-version`. |
| **Validation** | **Pydantic v2** models for agent outputs, config, and API DTOs | Typed boundaries between stages; matches PRD emphasis on structured reports and evidence fields. |
| **Migrations** | Start with **schema version** in DB + incremental SQL or **Alembic** if SQLAlchemy is adopted | Keep migrations explicit before multi-env deploys. |
| **Caching** | **None** in MVP except optional **in-memory** dedup for identical external fetches | Add Redis etc. only if rate limits or cost force it. |

### Authentication and security

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Practice MVP auth** | **Optional shared secret**: e.g. `Authorization: Bearer <token>` or `X-API-Key` from environment; **no** user directory | FR32 “access to outputs” for practice can be a single team key; FR26 enterprise SSO **out of scope** for MVP. |
| **Transport** | **TLS** in any shared/deployed environment; **localhost** OK for dev | NFR-S* baseline. |
| **Secrets** | **`pydantic-settings`** (or equivalent) loading from **env** / `.env` (gitignored); **never** log secret values or raw PHI | PRD excludes PHI by default; future FR34/FR35 need a different config profile. |
| **Authorization model** | **Single-tenant** deployment; **role-based views** deferred to growth | Matches scoping section. |

### API and communication patterns

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **External integrations** | **HTTP clients** (e.g. **`httpx`**) with **timeouts, retries, and structured error classification** | NFR-I1/I2, FR27–FR28 degradation. |
| **Internal pipeline** | **In-process** orchestration first (callable stages or a graph library added via `uv add`); **clear stage boundaries** (Clinical → Competitor → Consumer → Synthesis → Delivery) | PRD pipeline order; failure isolation (FR30). |
| **Trigger / status API** (if exposed) | **REST**, JSON, **`snake_case`** field names for stability with Python | Thin surface: `POST /runs`, `GET /runs/{id}`, `GET /runs/{id}/artifacts/...`. |
| **Long-running work** | **Async job pattern**: return **202** + `run_id`, poll status; avoid blocking HTTP threads on full pipeline | Demo-friendly status for Loom. |
| **Documentation** | **OpenAPI** if FastAPI (or similar) is introduced; otherwise **handwritten `docs/api.md`** | Consistency for agents. |

### Frontend architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **MVP UI** | **Report as artifact** (HTML/PDF/Markdown) + **email/file delivery**; optional **static** viewer (single page) that reads exported JSON | PRD emphasizes **consumption** of structured report, not a large SPA. |
| **State** | **Server-side truth** (run + artifacts); no Redux-class client state for MVP | Keeps practice build small. |
| **Future UI** | Defer **component framework** choice until a UX spec exists | Avoid premature React/Vue split. |

### Infrastructure and deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Hosting** | **Developer laptop / single VM / container** for practice; **no** multi-region requirement in MVP | Matches demo milestone. |
| **CI** | **GitHub Actions**: lint + tests on PR; optional **uv** cache | Repo already on GitHub. |
| **Config by environment** | **`ENV` or `.env`** with explicit **practice** vs **staging** profile names later | SaaS B2B section anticipates profiles—not all implemented now. |
| **Logging** | **Structured JSON** to stdout: **`run_id`**, **`correlation_id`**, **`stage`**, **`agent`**, level, message | NFR-O1/O2, demo narrative. |
| **Scaling** | **Vertical** scale first; **horizontal** workers only when schedule/load requires | Not optimizing for concurrency in MVP. |

### Decision impact analysis

**Implementation sequence (suggested):**

1. `uv init` + pin Python **3.12**; add **pydantic-settings**, **httpx**, **structlog** or stdlib `logging` JSON formatter.
2. SQLite schema for **runs**, **stages**, **artifact metadata**; filesystem layout for blobs.
3. Pipeline runner with **correlation ID** propagation and **per-stage** persistence.
4. Delivery adapter (email/file) and minimal **REST** or **CLI** trigger—whichever is first in epics.
5. CI workflow (ruff/pytest).

**Cross-component dependencies:**

- Artifact paths in DB **must** reference the configured root (portability).
- Auth secret **must** gate any network-facing API before shared deploy.
- Log fields **must** align with patterns so observability does not fragment across agents.

---

## Implementation patterns and consistency rules

### Pattern categories defined

**Critical conflict points for multi-agent coding:** JSON key casing, log field names, run/stage IDs, where tests live, and HTTP error mapping—without rules, implementations will diverge.

### Naming patterns

| Area | Rule | Example |
|------|------|---------|
| **Python modules** | **snake_case** file names | `clinical_agent.py`, `run_repository.py` |
| **Python symbols** | **snake_case** functions/vars; **PascalCase** classes | `run_id`, `class ClinicalAgent` |
| **DB tables/columns** | **snake_case** | `runs`, `correlation_id`, `started_at` |
| **REST paths** | **plural** resources, **kebab-case** multi-word segments if needed | `/runs`, `/runs/{run_id}/artifacts` |
| **JSON (API & logs)** | **snake_case** keys | `"run_id": "...", "stage": "synthesis"` |
| **Env vars** | **SCREAMING_SNAKE** | `PHARMA_RD_API_TOKEN`, `ARTIFACT_ROOT` |

### Structure patterns

| Area | Rule |
|------|------|
| **Tests** | **`tests/`** mirror package structure: `tests/agents/test_clinical.py`, `tests/integration/test_pipeline.py` |
| **Fixtures** | **`tests/fixtures/`** for JSON snapshots; **no** secrets in repo |
| **Config** | Single **`settings` module** (e.g. `pharma_rd/config.py`) used by all entrypoints |
| **Agents** | One package or subpackage per agent domain: e.g. `pharma_rd/agents/clinical/` |

### Format patterns

| Area | Rule |
|------|------|
| **Timestamps** | **ISO 8601** UTC in logs and JSON: `2026-04-04T12:00:00Z` |
| **Run identity** | **`run_id`**: opaque string (UUID preferred); **`correlation_id`**: same as `run_id` unless external systems supply another—document if split |
| **API errors** | JSON `{"error": {"code": "...", "message": "...", "detail": {}}}` with stable **`code`** enum for retries |
| **Success bodies** | Direct JSON objects or `{"data": ...}`—**pick one** per API version; default **direct** for minimal surface |

### Communication patterns

| Area | Rule |
|------|------|
| **Stage handoff** | **Pydantic models** per stage output; **version** field on each model when schemas evolve |
| **Events** | If added later: **dot-separated** names: `run.stage_completed` |

### Process patterns

| Area | Rule |
|------|------|
| **Retries** | **Idempotent** stage inputs where possible; retry only **transient** HTTP failures; cap attempts; log **final** failure with `run_id` |
| **Partial failure** | Persist completed stages; mark run **`partial_failed`** with **which** stage failed (FR30) |

### Enforcement guidelines

**All implementers must:**

- Use the **settings** module for config—no ad hoc `os.environ` reads scattered across files.
- Include **`run_id`** (and **`stage`** when applicable) on every log line in pipeline code.
- Add **tests** for new Pydantic models and stage contracts (serialization round-trip).

**Verification:** CI runs **ruff** + **pytest**; optional **mypy** if introduced.

### Pattern examples

**Good:** `logger.info("stage_finished", extra={"run_id": run_id, "stage": "synthesis"})` with JSON formatter.

**Anti-pattern:** Different JSON field names (`runId` vs `run_id`) between API and stored artifacts.

---

## Project structure and boundaries

### Complete project directory structure

Target layout after `uv init pharma_rd` (app name may match repo convention; adjust if monorepo keeps `pharma_rd/` inside `pharma_RD_workflow/`):

```
pharma_rd/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version          # 3.12
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── pharma_rd/
│       ├── __init__.py
│       ├── main.py              # CLI entry: trigger run, local dev
│       ├── config.py            # pydantic-settings
│       ├── logging_setup.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── runner.py        # orchestrates stages, correlation ID
│       │   └── state.py         # run state machine
│       ├── agents/
│       │   ├── clinical/
│       │   ├── competitor/
│       │   ├── consumer/
│       │   ├── synthesis/
│       │   └── delivery/
│       ├── integrations/        # HTTP clients, feed adapters
│       ├── persistence/
│       │   ├── db.py
│       │   ├── models.py        # SQLAlchemy or raw SQL helpers
│       │   └── artifacts.py
│       ├── delivery/            # email, file writers
│       └── api/                 # optional FastAPI app: routes/, deps.py
├── artifacts/                 # gitignored default root for outputs
├── data/                      # gitignored SQLite default path e.g. data/app.db
└── tests/
    ├── conftest.py
    ├── fixtures/
    ├── agents/
    ├── pipeline/
    └── integration/
```

### Architectural boundaries

| Boundary | Definition |
|----------|------------|
| **API** | **Thin** layer: validates auth token, maps HTTP ↔ `pipeline.runner`; **no** business logic in route handlers beyond orchestration glue. |
| **Agents** | **Own** domain prompts/parsing and **produce Pydantic outputs**; **do not** write to DB directly except via injected ports/repositories if you adopt hexagonal style. |
| **Persistence** | **Only** `persistence/` talks to SQLite and artifact store; agents return **data objects**, not SQL. |
| **Delivery** | **Consumes** final synthesis artifact + routing config; **does not** re-rank or alter evidence. |
| **Integrations** | **All** outbound HTTP here; central place for timeouts and error classification. |

### Requirements to structure mapping (PRD FR groups)

| FR group | Primary location |
|----------|------------------|
| **FR1–FR5** workflow orchestration | `pipeline/runner.py`, `pipeline/state.py`, `persistence/` |
| **FR6–FR13** monitoring agents | `agents/clinical/`, `agents/competitor/`, `agents/consumer/` |
| **FR14–FR17** synthesis | `agents/synthesis/` |
| **FR18–FR22** delivery & consumption | `agents/delivery/`, `delivery/` |
| **FR23–FR26** configuration | `config.py`, future `settings` profiles |
| **FR27–FR28** transparency / quiet runs | agent + synthesis **metadata** fields, logging |
| **FR29–FR31** operations & demo | `logging_setup.py`, `main.py`, CI |
| **FR32** access control | `api/deps.py` or CLI guard, env token |

### Integration points

| Kind | Detail |
|------|--------|
| **Internal** | Runner calls agents **in order**; each handoff is **in-memory** Pydantic → persisted JSON + DB row. |
| **External** | `integrations/*` only; rate limits and keys centralized. |
| **Data flow** | Trigger → **run row** → stages → **artifact files** → **delivery** → optional **email** / file drop. |

### File organization patterns

- **Configuration:** `config.py` + `.env.example` only; secrets never committed.
- **Tests:** Cohesive **fixtures** for sample agent JSON under `tests/fixtures/`.
- **Docs:** Optional `docs/architecture-notes.md` for humans—**not** required for MVP (avoid doc sprawl per project norms).

---

## Architecture validation results

### Coherence validation

**Decision compatibility:** Python **3.12** + **uv** + **SQLite** + **filesystem artifacts** + **Pydantic** are a common, compatible stack; no conflicting choices (e.g. no second primary DB).

**Pattern consistency:** **snake_case** JSON aligns with Python and SQLite; REST and logging share field names.

**Structure alignment:** Directory layout covers **pipeline**, **agents**, **persistence**, **integrations**, and **delivery**—matching PRD stages.

### Requirements coverage validation

**Functional:** FR1–FR32 are mappable to **runner**, **per-agent packages**, **persistence**, **delivery**, and **config**. FR33–FR35 are **explicitly deferred** with roadmap references—acceptable for practice architecture.

**Non-functional:** Performance (timeouts/retries), security (secrets, TLS posture), reliability (durable runs, partial failure), observability (structured logs, `run_id`), and integration degradation are **addressed** at architectural level.

### Implementation readiness validation

**Decisions:** Critical choices documented; Python support window verified via current **3.12** status on python.org / devguide.

**Structure:** Concrete tree provided—not generic placeholders.

**Gaps (non-blocking):** Exact choice of **orchestration library** (plain functions vs LangGraph) remains an **implementation** decision once first spike is run; **email provider** (SMTP vs SendGrid) is an integration detail.

### Architecture completeness checklist

- [x] Project context analyzed (steps 1–2)
- [x] Starter template evaluated (step 3)
- [x] Core decisions: data, auth, API, frontend posture, infra (step 4)
- [x] Implementation patterns (step 5)
- [x] Project structure & boundaries (step 6)
- [x] Validation & gaps (step 7)

### Architecture readiness assessment

**Overall status:** **Ready for implementation** (practice MVP scope).

**Confidence:** **High** for pipeline + artifacts + observability; **medium** for long-term enterprise hardening—by design deferred.

**Strengths:** Clear **stage boundaries**, **durable** run model, **demo-friendly** logging contract.

**Future enhancement:** SSO, multi-tenant DB, PHI, and **audit** depth when FR33–FR35 are activated.

### Implementation handoff

**Guidelines for implementers:** Follow this document for **boundaries** and **patterns**; extend **Pydantic** models coherently when FRs add fields.

**First implementation priority:** Run **`uv init pharma_rd`** (or equivalent) and **`uv python pin 3.12`**, then implement **persistence + runner skeleton** with **correlation ID** logging end-to-end.

---

## Workflow completion

The **bmad-create-architecture** workflow is **complete** for **pharma_RD_workflow**. The canonical technical reference is **`_bmad-output/planning-artifacts/architecture.md`**.

**Suggested next step:** Use **`bmad-help`** (or your BMM menu) to pick the next workflow—typically **epics/stories** or **implementation** planning aligned with the PRD.

If you want to adjust any decision (e.g. add **FastAPI** in MVP vs CLI-only first), say which section to revise and we can update this document.
