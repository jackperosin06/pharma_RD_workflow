---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
workflowType: epics-and-stories
project_name: pharma_RD_workflow
user_name: Jackperosin_
date: '2026-04-06'
status: complete
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/product-brief-pharma_RD_workflow.md
---

# pharma_RD_workflow - Epic Breakdown

## Overview

This document provides the epic and story breakdown for **pharma_RD_workflow**, decomposing the PRD functional and non-functional requirements, architecture decisions, and product brief into implementable stories with acceptance criteria.

## Requirements Inventory

### Functional Requirements

```
FR1: Workflow operator can start a full pipeline run on demand.
FR2: Workflow operator can configure a recurring schedule for pipeline runs (default: weekly).
FR3: System can execute agent stages in the required order with defined handoffs between stages.
FR4: System can persist intermediate outputs between stages for a given run identifier.
FR5: System can associate all stage outputs with a single run (correlation) for traceability and demo.
FR6: Clinical Data Agent can discover and summarize new or updated clinical trial publications relevant to configured therapeutic areas.
FR7: Clinical Data Agent can ingest internal research summaries when supplied via configured inputs (including stub/sample data for practice).
FR8: Competitor Intelligence Agent can track competitor product approvals and material regulatory disclosures for configured competitors.
FR9: Competitor Intelligence Agent can track pipeline disclosures relevant to configured watch scopes.
FR10: Competitor Intelligence Agent can flag significant patent filing activity for configured competitors.
FR11: Consumer Insight Agent can process consumer feedback signals from configured sources (public/mock as scoped).
FR12: Consumer Insight Agent can incorporate pharmacy sales trend signals when those feeds are configured and available.
FR13: Consumer Insight Agent can surface unmet need / demand signals from configured market sources.
FR14: Synthesis Agent can consume the structured outputs of the Clinical, Competitor, and Consumer agents for a run.
FR15: Synthesis Agent can cross-reference signals across domains to produce a ranked list of formulation or line-extension opportunities.
FR16: For each ranked item, Synthesis Agent can attach supporting evidence references suitable for human verification.
FR17: For each ranked item, Synthesis Agent can provide a commercial viability assessment section (qualitative in MVP unless otherwise specified).
FR18: Delivery Agent can render a structured insight report for a completed run.
FR19: Delivery Agent can distribute the report to configured R&D scientist and marketing lead recipients (channel: email, file drop, or in-app viewer—implementation open).
FR20: R&D scientist can open and read the structured insight report for a given run.
FR21: Marketing lead can open and read the same structured insight report for a given run.
FR22: Report presentation can make clear that items are recommendations and that pursuit decisions remain human-owned.
FR23: Workflow operator can configure therapeutic area scope and boundaries for monitoring.
FR24: Workflow operator can configure competitor watchlists and related keywords or identifiers.
FR25: Workflow operator can configure connection settings for external data sources permitted in the deployment (public APIs, files, stubs).
FR26: System can operate in practice mode using public and/or mock sources without requiring enterprise SSO.
FR27: Structured report can state when little net-new signal was found versus material changes.
FR28: Structured report can summarize what was scanned (sources/scopes) for the run at a high level.
FR29: Workflow operator can view per-agent status for an execution.
FR30: Workflow operator can retry a failed stage when supported without manually re-creating upstream artifacts.
FR31: System can emit run history and logs sufficient to produce a demonstration recording of agent execution and final delivery.
FR32: Organization can restrict access to reports to authorized users or distribution lists (exact mechanism implementation-open; may be coarse in practice builds).
FR33: (Phase 2) System can alert stakeholders to major external events between scheduled runs.
FR34: (Phase 2) Admin can integrate enterprise SSO and centralized secrets management for connectors.
FR35: (Phase 3) System can support enterprise audit, PHI-aware feeds, and multi-tenant isolation where productized.
```

### NonFunctional Requirements

```
NFR-P1: Full pipeline run completes within a predictable window suitable for a recorded demo (target: under 60 minutes wall-clock for MVP practice configuration; configurable timeout per stage).
NFR-P2: Recipients can open and read a delivered report on typical corporate hardware without specialized client software (browser or standard email/PDF—implementation open).
NFR-P3: External source calls use timeouts and bounded retries so one slow feed does not block the entire run indefinitely without operator visibility.
NFR-S1: Secrets are not stored in source control; injected via environment or deployment-appropriate secrets mechanism.
NFR-S2: Report artifacts and logs are access-controlled to authorized roles/distribution lists (see FR32).
NFR-S3: Data in transit between components and external APIs uses TLS where APIs support it.
NFR-S4: MVP assumes no PHI in prompts/logs; if PHI is later in scope, processing must follow an approved privacy design (out of MVP).
NFR-R1: Failed stages are visible to the workflow operator with actionable error summaries (not silent failure).
NFR-R2: Run history is durable enough to answer what ran, when, and what failed for demo and debug (minimum retention: configurable; default 30 days for practice unless otherwise set).
NFR-R3: Idempotent or safe retry semantics for stage reruns where FR30 applies (no duplicate conflicting artifacts without clear versioning).
NFR-I1: Connectors declare expected data formats and degrade gracefully when a source returns empty or partial data (report still generated with transparency per FR27–FR28).
NFR-I2: Integration failures are classified (auth, rate limit, schema change, network) in logs to shorten operator time-to-fix.
NFR-O1: Each run emits a correlation identifier propagated across stages (aligns with FR5).
NFR-O2: Structured logs contain stage name, start/end, and outcome suitable for Loom-style narration.
```

### Additional Requirements

_From Architecture (`architecture.md`):_

- Initialize application with **`uv init`** (or equivalent) and pin **Python 3.12** via `uv python pin` / `.python-version`.
- **SQLite** for run/stage metadata; **filesystem** artifact root for intermediate and final outputs; paths recorded in DB.
- **Pydantic v2** for stage outputs, configuration DTOs, and API payloads where applicable.
- **Structured logging** (JSON to stdout) with **`run_id`**, **`stage`**, correlation, outcome—consistent field names (`snake_case`).
- **Optional REST** surface: async job pattern for long runs (`POST /runs`, poll status); or **CLI-first** if API deferred—document chosen entrypoint per increment.
- **Secrets** via `pydantic-settings` / environment; never log secrets (NFR-S1).
- **CI** (e.g. GitHub Actions): lint + tests on PR.
- **snake_case** JSON and REST conventions; **ISO 8601** UTC timestamps in logs and APIs.

### UX Design Requirements

_No UX design specification document was present under `planning-artifacts`. Report consumption may use **email**, **file drop**, or a **minimal static viewer** per PRD—captured under Epic 7 stories._

### FR Coverage Map

| FR | Epic | Notes |
|----|--------|--------|
| FR1 | Epic 1 | On-demand run trigger |
| FR2 | Epic 2 | Schedule configuration |
| FR3 | Epic 1 | Ordered stages with handoffs |
| FR4 | Epic 1 | Persist intermediate outputs |
| FR5 | Epic 1 | Single run correlation |
| FR6–FR7 | Epic 3 | Clinical agent |
| FR8–FR10 | Epic 4 | Competitor agent |
| FR11–FR13 | Epic 5 | Consumer agent |
| FR14–FR17 | Epic 6 | Synthesis |
| FR27–FR28 | Epic 6 | Transparency in structured output |
| FR18–FR22 | Epic 7 | Delivery & consumption |
| FR23–FR26 | Epic 8 | Configuration & practice mode |
| FR29 | Epic 1 | Per-agent status (extended in Epic 2 for failure states) |
| FR30 | Epic 2 | Stage retry |
| FR31 | Epic 1, 7 | Demo-grade history + delivery proof |
| FR32 | Epic 8 | Coarse access control |
| FR33–FR35 | — | **Out of MVP** (roadmap only) |

### LLM enhancement stories (OpenAI GPT-4o)

Post-baseline stories add **model-assisted analysis** on top of existing fetch/aggregate behavior. Full specs live under **`_bmad-output/implementation-artifacts/`**.

| Story | Epic | Summary |
|-------|------|---------|
| **3.3** | Epic 3 | GPT clinical analyst after PubMed fetch → `ClinicalOutput` enrichment |
| **4.4** | Epic 4 | GPT competitive intelligence after FDA/regulatory fetch → `CompetitorOutput` enrichment |
| **5.4** | Epic 5 | GPT market analyst after consumer signals → `ConsumerOutput` enrichment |
| **6.5** | Epic 6 | Replace deterministic synthesis with GPT strategy advisor; **must** validate to `SynthesisOutput` |
| **7.6** | Epic 7 | GPT-generated CEO-ready HTML/Markdown report narrative; FR22 + sanitization |

**Recommended order:** **3.3 → 4.4 → 5.4** (parallelizable after shared OpenAI client) → **6.5** → **7.6**.

## Epic List

### Epic 1: Executable pipeline foundation

Operators and implementers can run an end-to-end **pharma_RD** pipeline with **stub or minimal agents**, **durable run and stage state**, **correlated logs**, and **visibility** suitable for a demo recording—establishing the technical backbone for real agents in later epics.

**FRs covered:** FR1, FR3, FR4, FR5, FR29, FR31 (with Epic 7 for full delivery proof)

**NFRs addressed:** NFR-O1, NFR-O2, NFR-R1, NFR-R2 (baseline), foundational alignment with NFR-P1/P3 via timeouts in later epic

---

### Epic 2: Scheduling and resilient execution

Workflow operators can configure **recurring runs**, rely on **timeouts and bounded retries** on external calls, **retry failed stages** without redoing completed work, and operate within **predictable wall-clock** behavior for demos.

**FRs covered:** FR2, FR30

**NFRs addressed:** NFR-P1, NFR-P3, NFR-R3

---

### Epic 3: Clinical Data Agent

The system produces **structured clinical monitoring output** for each run: **publication discovery/summary** for configured TAs and **internal research ingestion** when configured (including stubs).

**FRs covered:** FR6, FR7; **Story 3.3** extends interpretation via GPT (see LLM enhancement table).

**NFRs addressed:** NFR-I1, NFR-I2, NFR-S3 (where applicable)

---

### Epic 4: Competitor Intelligence Agent

The system tracks **approvals/disclosures**, **pipeline disclosures** within watch scopes, and **patent filing** signals for configured competitors.

**FRs covered:** FR8, FR9, FR10; **Story 4.4** extends interpretation via GPT (see LLM enhancement table).

**NFRs addressed:** NFR-I1, NFR-I2, NFR-S3

---

### Epic 5: Consumer Insight Agent

The system surfaces **consumer feedback**, optional **pharmacy sales trends**, and **unmet need / demand** signals from configured (including mock) sources.

**FRs covered:** FR11, FR12, FR13; **Story 5.4** extends interpretation via GPT (see LLM enhancement table).

**NFRs addressed:** NFR-I1, NFR-I2, NFR-S3

---

### Epic 6: Synthesis — ranking, evidence, and transparency

The Synthesis step **consumes** the three monitoring agents’ outputs, **cross-references** domains into a **ranked opportunity list** with **evidence** and **commercial viability**, and embeds **quiet-run** and **scan summary** transparency.

**FRs covered:** FR14, FR15, FR16, FR17, FR27, FR28; **Story 6.5** replaces deterministic core with GPT strategy synthesis while keeping **`SynthesisOutput`** contract (see LLM enhancement table).

**NFRs addressed:** NFR-I1 (graceful partial inputs)

---

### Epic 7: Delivery and consumption

The Delivery step **renders** the structured insight report, **distributes** it to R&D and marketing recipients (e.g. file drop, optional **Slack incoming webhook** notification), ensures **readability** without specialized clients, and **frames recommendations as human-owned** decisions.

**FRs covered:** FR18, FR19, FR20, FR21, FR22 (FR31 completion for demo narrative); **Story 7.6** adds GPT-authored HTML/Markdown narrative (see LLM enhancement table).

**NFRs addressed:** NFR-P2, NFR-S2 (with Epic 8)

---

### Epic 8: Configuration, practice mode, and access

Operators configure **TA scope**, **competitor watchlists**, and **connector settings**; the deployment runs in **practice mode** without SSO; **coarse access control** protects reports and logs.

**FRs covered:** FR23, FR24, FR25, FR26, FR32

**NFRs addressed:** NFR-S1, NFR-S2, NFR-S4 (assumption: no PHI)

---

### Roadmap (not in MVP contract)

- **FR33–FR35:** Alerting, enterprise SSO/secrets, audit/PHI/multi-tenant—track in product roadmap; no MVP stories.

---

## Epic 1: Executable pipeline foundation

**Goal:** Establish the **uv**-based Python project, **persistence** for runs and stages, **ordered pipeline execution** with **persisted handoffs**, **correlation IDs** and **structured logging**, and **operator visibility** into run and per-stage status for demo (Loom-ready).

### Story 1.1: Initialize project from architecture baseline

As a **developer**,
I want **the repository scaffolded with `uv`, Python 3.12, and core dependencies**,
So that **all subsequent work matches the architecture baseline and CI can run consistently**.

**Implements:** Architecture starter (uv, pin), NFR-S1 (no secrets in repo—`.env.example` only).

**Acceptance Criteria:**

**Given** a clean checkout of `pharma_RD_workflow`
**When** the developer follows the documented init steps (`uv init`, `uv python pin 3.12`, add `pydantic`, `pydantic-settings`, `httpx`, dev tools as per architecture)
**Then** `uv run` executes a minimal entrypoint without error
**And** `pyproject.toml` and lockfile are committed; `.env.example` lists non-secret keys only
**And** GitHub Actions (or documented equivalent) runs **lint + tests** on PR

---

### Story 1.2: Persist runs and stages in SQLite

As a **workflow operator**,
I want **each pipeline run and stage recorded durably**,
So that **I can inspect what ran and what failed after the fact** (NFR-R2).

**Implements:** FR4 (foundation), FR5 (run record), architecture data layer.

**Acceptance Criteria:**

**Given** the configured SQLite path and schema migration or versioned DDL
**When** a run is created
**Then** a row exists with **run_id**, timestamps, and overall status
**And** each stage execution writes/updates a stage row linked to **run_id** with status (`pending`, `running`, `completed`, `failed`)
**And** retention policy is **configurable** with default **30 days** for practice (NFR-R2)

---

### Story 1.3: Pipeline runner with ordered stages and artifact handoffs

As a **workflow operator**,
I want **stages to execute in the required order with persisted outputs between stages**,
So that **handoffs match the PRD pipeline model** (Clinical → Competitor → Consumer → Synthesis → Delivery).

**Implements:** FR3, FR4.

**Acceptance Criteria:**

**Given** a run is started
**When** each stage completes
**Then** its **structured output** (Pydantic-validated JSON) is written to the **artifact store** and metadata (path, hash) stored in SQLite
**And** the next stage receives the **previous outputs** as defined by the pipeline contract
**And** stub implementations may return minimal valid payloads until real agents exist

---

### Story 1.4: Correlation ID and structured logging

As a **workflow operator**,
I want **every log line tied to a run and stage with a consistent correlation identifier**,
So that **I can narrate a demo and debug failures** (NFR-O1, NFR-O2, FR5).

**Acceptance Criteria:**

**Given** a run has started with **run_id** (used as correlation unless overridden)
**When** any pipeline or agent code emits logs
**Then** each log entry is **structured JSON** including **run_id**, **stage**, start/end or outcome, and level
**And** the same **run_id** appears in DB rows and artifact paths for that run

---

### Story 1.5: On-demand pipeline run trigger

As a **workflow operator**,
I want **to start a full pipeline run on demand**,
So that **I can demo or test without waiting for a schedule** (FR1).

**Acceptance Criteria:**

**Given** valid configuration (stub sources acceptable)
**When** the operator invokes the documented trigger (**CLI** command, or `POST /runs` if API is implemented in this increment)
**Then** a new **run_id** is created and the pipeline executes through stub or available stages
**And** the command returns **run_id** and a pointer to **poll status** if async

---

### Story 1.6: Per-agent status and run history for operators

As a **workflow operator**,
I want **to see per-agent (stage) status and historical runs**,
So that **I can verify execution for a recording and troubleshoot** (FR29, FR31).

**Acceptance Criteria:**

**Given** at least one completed or failed run exists
**When** the operator uses the **CLI status** subcommand or **GET /runs/{id}** (if API exists)
**Then** they see **per-stage status**, timestamps, and error summaries for failures (NFR-R1)
**And** run listing supports **demo-friendly** filtering (e.g. last N runs)

---

## Epic 2: Scheduling and resilient execution

**Goal:** Enable **recurring schedules**, **stage timeouts and bounded retries** for integrations, and **retry of failed stages** without redoing successful upstream work.

### Story 2.1: Recurring schedule for pipeline runs

As a **workflow operator**,
I want **to configure a recurring schedule with weekly default**,
So that **reports run without manual triggers** (FR2).

**Acceptance Criteria:**

**Given** schedule settings in configuration (cron expression or equivalent)
**When** the scheduler process runs
**Then** pipeline runs start according to the configured cadence with **weekly** as the documented default
**And** schedule changes take effect without code deploy (config reload or documented restart)

---

### Story 2.2: Per-stage timeouts and bounded retries for external calls

As a **workflow operator**,
I want **external calls to time out and retry within bounds**,
So that **one slow source cannot hang the entire run invisibly** (NFR-P3, NFR-P1).

**Acceptance Criteria:**

**Given** connector HTTP calls use shared client settings
**When** a source exceeds the configured timeout or returns transient errors
**Then** retries occur up to a **bounded** count with backoff
**And** failure after retries marks the stage **failed** with an **actionable** message (NFR-R1) and **classified** reason where possible (NFR-I2)

---

### Story 2.3: Retry failed stage without re-running completed upstream

As a **workflow operator**,
I want **to retry only a failed stage** when supported,
So that **I do not manually recreate upstream artifacts** (FR30, NFR-R3).

**Acceptance Criteria:**

**Given** a run where upstream stages **completed** and a downstream stage **failed**
**When** the operator invokes **stage retry**
**Then** the system re-executes **only** the failed stage (and downstream dependents if any) using **persisted upstream artifacts**
**And** artifact versioning or run metadata prevents **silent overwrites**; conflicts are explicit in logs

---

## Epic 3: Clinical Data Agent

**Goal:** Replace stubs with **real Clinical agent behavior** for TA-scoped publication signal and **internal research** ingestion (including sample/stub files).

### Story 3.1: Discover and summarize clinical trial publications for configured TAs

As a **workflow operator**,
I want **the Clinical agent to discover and summarize relevant clinical trial publications**,
So that **R&D sees up-to-date trial signal** for configured therapeutic areas (FR6).

**Acceptance Criteria:**

**Given** TA scope from configuration (Epic 8)
**When** the Clinical stage runs for a **run_id**
**Then** output includes **summaries** of new or updated **trial publications** relevant to the TA with **references** suitable for human follow-up
**And** empty or partial source data degrades per NFR-I1 with explicit notes in structured output

---

### Story 3.2: Ingest internal research summaries (including stub/sample path)

As a **workflow operator**,
I want **internal research summaries merged when configured**,
So that **practice mode can use sample data** without live internal systems (FR7).

**Acceptance Criteria:**

**Given** a configured path or stub for internal research artifacts
**When** the Clinical stage runs
**Then** structured output incorporates **internal research** content when present
**And** when not configured, the stage still succeeds with **explicit “not configured”** in output (NFR-I1)

---

### Story 3.3: GPT-powered clinical analysis

As a **workflow operator**,
I want **PubMed/publication fetch results passed to GPT-4o as a pharma R&D analyst**,
So that **significance, TA relevance, and trial prioritization for iNova** are interpreted, not only listed (extends FR6).

**Specification:** `_bmad-output/implementation-artifacts/3-3-gpt-powered-clinical-analysis.md`

**Acceptance Criteria (summary):**

**Given** fetch completes and **`PHARMA_RD_OPENAI_API_KEY`** is set  
**When** the Clinical stage runs  
**Then** OpenAI (**gpt-4o**, configurable) receives system + user prompts with **TA scope** and publication payload; **`ClinicalOutput`** gains validated analyst fields; tests **mock** the API (NFR-S1).

---

## Epic 4: Competitor Intelligence Agent

**Goal:** Deliver **competitor approvals/disclosures**, **pipeline disclosures**, and **patent filing** signals per watchlists.

### Story 4.1: Track approvals and regulatory disclosures

As a **workflow operator**,
I want **competitor approvals and material regulatory disclosures tracked** for configured competitors,
So that **we do not miss competitive regulatory moves** (FR8).

**Acceptance Criteria:**

**Given** competitor watchlist configuration
**When** the Competitor stage runs
**Then** structured output lists **approvals** and **disclosures** found in the observation window with **sources**
**And** integration failures are **classified** in logs (NFR-I2)

---

### Story 4.2: Pipeline disclosure watch scopes

As a **workflow operator**,
I want **pipeline disclosures captured for configured watch scopes**,
So that **we see pipeline-relevant competitor activity** (FR9).

**Acceptance Criteria:**

**Given** watch scopes in configuration
**When** the Competitor stage runs
**Then** output includes **pipeline disclosure** items matching scope or explicitly states **none found**
**And** partial data paths remain **transparent** in output (NFR-I1)

---

### Story 4.3: Patent filing flags

As a **workflow operator**,
I want **significant patent filing activity flagged** for configured competitors,
So that **IP pressure is visible early** (FR10).

**Acceptance Criteria:**

**Given** configured competitors and keyword/patent feeds where available
**When** the Competitor stage runs
**Then** output includes **patent-related flags** with references or **explicit empty** state
**And** TLS used for external APIs where supported (NFR-S3)

---

### Story 4.4: GPT-powered competitor analysis

As a **workflow operator**,
I want **FDA/regulatory fetch results passed to GPT-4o as a pharmaceutical competitive intelligence analyst**,
So that **strategic significance, threats, opportunities, and urgent items** are interpreted (extends FR8–FR10).

**Specification:** `_bmad-output/implementation-artifacts/4-4-gpt-powered-competitor-analysis.md`

**Acceptance Criteria (summary):**

**Given** competitor stage data is assembled and the API key is set  
**When** the Competitor stage runs  
**Then** GPT-4o enriches **`CompetitorOutput`**; degradation policy **aligned** with Story 3.3; tests use mocks.

---

## Epic 5: Consumer Insight Agent

**Goal:** Produce **consumer**, **sales trend**, and **demand** signals from configured public/mock sources.

### Story 5.1: Consumer feedback signals

As a **workflow operator**,
I want **consumer feedback processed from configured sources**,
So that **market voice informs synthesis** (FR11).

**Acceptance Criteria:**

**Given** configured consumer sources (may be mock)
**When** the Consumer stage runs
**Then** structured output includes **feedback themes** with **sources**
**And** mock mode is **explicit** in configuration and output when used (FR26 alignment)

---

### Story 5.2: Pharmacy sales trend signals when configured

As a **marketing lead**,
I want **pharmacy sales trends included when feeds exist**,
So that **commercial framing is grounded** where data allows (FR12).

**Acceptance Criteria:**

**Given** optional sales feed configuration
**When** feeds are **unavailable** or **empty**
**Then** the stage still completes with **transparent** explanation (NFR-I1)
**When** feeds return data
**Then** trends are summarized in structured output with **scope** stated

---

### Story 5.3: Unmet need and demand signals

As a **workflow operator**,
I want **unmet need / demand signals from market sources**,
So that **synthesis can rank opportunities with demand context** (FR13).

**Acceptance Criteria:**

**Given** configured market sources
**When** the Consumer stage runs
**Then** output includes **demand/unmet need** signals or explicit **insufficient signal** wording
**And** outputs remain **non-PHI** by default (NFR-S4)

---

### Story 5.4: GPT-powered consumer insight analysis

As a **workflow operator**,
I want **aggregated consumer signals passed to GPT-4o as a pharmaceutical market analyst**,
So that **unmet needs, demand patterns, and line-extension relevance** are interpreted (extends FR11–FR13).

**Specification:** `_bmad-output/implementation-artifacts/5-4-gpt-powered-consumer-insight-analysis.md`

**Acceptance Criteria (summary):**

**Given** consumer stage payload is assembled and the API key is set  
**When** the Consumer stage runs  
**Then** **`ConsumerOutput`** is enriched; degradation **aligned** with Stories 3.3 / 4.4; mocks in CI.

---

## Epic 6: Synthesis — ranking, evidence, and transparency

**Goal:** **Cross-domain synthesis**: ranked opportunities with **evidence**, **commercial viability**, **quiet-run** messaging, and **scan summary**.

### Story 6.1: Consume monitoring agent outputs for a run

As a **workflow operator**,
I want **Synthesis to load Clinical, Competitor, and Consumer outputs for the same run**,
So that **ranking uses a single coherent snapshot** (FR14).

**Acceptance Criteria:**

**Given** prior stages persisted outputs for **run_id**
**When** the Synthesis stage runs
**Then** it **fails fast** with a clear error if any required upstream artifact is missing
**And** when upstream is partial, synthesis proceeds with **documented gaps** (NFR-I1)

---

### Story 6.2: Ranked opportunities with cross-domain cross-reference

As a **R&D scientist**,
I want **a ranked list of formulation or line-extension opportunities with cross-domain rationale**,
So that **I can prioritize judgment time** (FR15).

**Acceptance Criteria:**

**Given** valid upstream structured inputs
**When** Synthesis completes
**Then** output contains a **ranked list** with **short rationale** tying clinical, competitor, and consumer signals
**And** ranking criteria are **versioned** in metadata for auditability

---

### Story 6.3: Evidence references and commercial viability per item

As a **R&D scientist**,
I want **each ranked item to include verifiable evidence and commercial viability framing**,
So that **I can validate claims before pursuit** (FR16, FR17).

**Acceptance Criteria:**

**Given** a ranked item in synthesis output
**When** reviewed by a human
**Then** each item includes **references** or links suitable for **verification** (FR16)
**And** each item includes a **qualitative commercial viability** section (FR17)

---

### Story 6.4: Quiet-run and scan-summary transparency in synthesis output

As a **marketing lead**,
I want **the synthesis output to distinguish low-signal runs and summarize what was scanned**,
So that **I trust the report when little changed** (FR27, FR28).

**Acceptance Criteria:**

**Given** any run
**When** Synthesis completes
**Then** structured output includes **net-new vs quiet** characterization (FR27)
**And** includes a **high-level summary of sources/scopes scanned** (FR28)

---

### Story 6.5: GPT-powered synthesis

As a **workflow operator**,
I want **Synthesis to use GPT-4o as a pharmaceutical strategy advisor across all three monitoring outputs**,
So that **ranking, rationale, cross-domain reasoning, and urgency** replace deterministic logic while **`SynthesisOutput`** remains **Pydantic-valid** (FR14–FR17, FR27–FR28).

**Specification:** `_bmad-output/implementation-artifacts/6-5-gpt-powered-synthesis.md`

**Acceptance Criteria (summary):**

**Given** upstream outputs (including GPT fields from 3.3–5.4 when present)  
**When** the API key is set  
**Then** **deterministic synthesis path is not used** for that run (or behind explicit flag); model output **parses to** **`SynthesisOutput`**; invalid JSON handled per spec; tests mock OpenAI.

---

## Epic 7: Delivery and consumption

**Goal:** **Render** the final insight report, **distribute** to recipients (including optional **Slack** summaries), support **reading** without special clients, and **human-judgment** framing.

### Story 7.1: Render structured insight report artifact

As a **workflow operator**,
I want **a rendered structured insight report for each completed run**,
So that **recipients receive a consistent deliverable** (FR18).

**Acceptance Criteria:**

**Given** synthesis output for **run_id**
**When** Delivery runs
**Then** a **report artifact** is produced (e.g. HTML, PDF, or Markdown bundle) under the artifact root with metadata in DB
**And** report structure matches the **schema** agreed in implementation (sections for summary, ranked list, evidence, governance disclaimer)

---

### Story 7.2: Distribute report to R&D and marketing recipients

As a **workflow operator**,
I want **the report distributed via email or file drop (or equivalent)**,
So that **the intended audience receives it on schedule** (FR19).

**Acceptance Criteria:**

**Given** recipient list and channel settings in configuration
**When** distribution runs
**Then** **R&D scientist** and **marketing lead** addresses receive the report or a secure link/path per configuration
**And** failures are **logged** with **actionable** errors (NFR-R1)

---

### Story 7.3: Recipients open and read the report

As an **R&D scientist** or **marketing lead**,
I want **to open and read the structured report on standard hardware**,
So that **I can consume insights without special software** (FR20, FR21, NFR-P2).

**Acceptance Criteria:**

**Given** a delivered artifact or link
**When** the recipient opens it on a typical corporate laptop (browser or email/PDF)
**Then** the **ranked opportunities**, **evidence**, and **summary** are readable
**And** no proprietary client install is required (NFR-P2)

---

### Story 7.4: Human-owned pursuit language in the report

As a **compliance-conscious stakeholder**,
I want **clear language that recommendations are not approvals**,
So that **pursuit remains explicitly human-owned** (FR22).

**Acceptance Criteria:**

**Given** any rendered report
**When** a recipient reads the executive section and each opportunity
**Then** **disclaimer language** states items are **recommendations** and **pursuit decisions are human-owned**
**And** disclaimer is **visible** (e.g. summary + footer), not buried-only

---

### Story 7.5: Slack webhook delivery

As a **workflow operator** or **report recipient**,
I want **a Slack notification with key insight-run context when a webhook URL is configured**,
So that **R&D and marketing see signal highlights and where to open the full HTML report without polling** (extends FR19 delivery surfaces).

**Acceptance Criteria:**

**Given** **`PHARMA_RD_SLACK_WEBHOOK_URL`** is set  
**When** Delivery has written **`report.html`** to the artifact root  
**Then** a **Slack Block Kit** message is **POST**ed to the webhook with **branding**, **run date**, **signal characterization** summary, **top ranked opportunities** (short rationale + commercial viability excerpt), **monitoring scope** (therapeutic areas and competitor watchlists from configuration), **FR22** disclaimer text, and a **report location** line (MVP: **on-disk path** to the HTML file; designed so a **URL** can replace the path later without rewriting Block assembly)

**Given** the webhook URL is **not** set  
**When** Delivery runs  
**Then** Slack is **skipped** with a **structured INFO log** (no crash, no error)

**Given** Slack POST **fails**  
**When** the error is handled  
**Then** the failure is **logged** with actionable detail and the run does **not** fail solely because of Slack (NFR-R1 alignment)

---

### Story 7.6: GPT-powered report narrative and formatting

As a **workflow operator**,
I want **`report.html` / `report.md` produced by GPT-4o as a senior pharmaceutical strategy consultant**,
So that **executive prose, narrative per opportunity, commercial conclusion, FR22 disclaimer, and CEO-ready HTML styling** replace template assembly (extends FR18, FR22).

**Specification:** `_bmad-output/implementation-artifacts/7-6-gpt-powered-report-narrative-and-formatting.md`

**Acceptance Criteria (summary):**

**Given** **`SynthesisOutput`** exists and the API key is set  
**When** Delivery runs  
**Then** OpenAI returns **sanitized** HTML suitable for browser + Slack; **FR22** visible; distribution and **7.5** Slack remain functional; tests mock API.

---

## Epic 8: Configuration, practice mode, and access

**Goal:** Operators configure **scope**, **watchlists**, and **connectors**; deployment stays in **practice mode** without SSO; **coarse access** to reports and logs.

### Story 8.1: Therapeutic area scope configuration

As a **workflow operator**,
I want **to configure therapeutic area scope and boundaries**,
So that **agents monitor the right franchise** (FR23).

**Acceptance Criteria:**

**Given** configuration file or settings UI/API
**When** TA scope is saved
**Then** Clinical and downstream stages **read** the same validated scope model
**And** invalid configuration fails validation at startup or save with **clear errors**

---

### Story 8.2: Competitor watchlists and identifiers

As a **workflow operator**,
I want **competitor watchlists with keywords or identifiers**,
So that **Competitor agent tracking matches our strategy** (FR24).

**Acceptance Criteria:**

**Given** watchlist configuration
**When** the Competitor stage runs
**Then** it uses **only** configured competitors and related identifiers
**And** empty watchlist is rejected or handled with **explicit** operator warning

---

### Story 8.3: Connection settings for permitted external sources

As a **workflow operator**,
I want **connection settings for permitted APIs, files, and stubs**,
So that **integrations are configurable per deployment** (FR25, NFR-S1).

**Acceptance Criteria:**

**Given** non-secret settings in config and **secrets** in environment only
**When** connectors initialize
**Then** they receive **timeouts**, **base URLs**, and **credentials** from secure sources
**And** no secrets appear in logs or repo (NFR-S1)

---

### Story 8.4: Practice mode without enterprise SSO

As a **workflow operator**,
I want **the system to run in practice mode on public/mock data without SSO**,
So that **we can demo before enterprise IdP** (FR26).

**Acceptance Criteria:**

**Given** `practice` (or equivalent) profile is enabled
**When** the system runs
**Then** **no SSO** is required for operation
**And** mock/public sources are **labeled** in config and optionally in reports

---

### Story 8.5: Coarse access control for reports and logs

As an **organization administrator**,
I want **reports and logs restricted to authorized users or lists**,
So that **insight artifacts are not world-readable** (FR32, NFR-S2).

**Acceptance Criteria:**

**Given** deployment exposes HTTP or shared storage
**When** an unauthenticated or unauthorized request accesses report or history endpoints
**Then** access is **denied**
**And** authorized paths include at least **API key / bearer** or **distribution-list equivalent** per architecture
**And** practice builds may use a **single shared key** documented in runbooks

---

## Final validation

### FR coverage

- **FR1–FR32** (MVP) are covered by Stories **1.1–8.5** and the FR coverage map.
- **Stories 3.3, 4.4, 5.4, 6.5, 7.6** deepen LLM-assisted interpretation and reporting while **remaining traceable** to the same FR IDs (see **LLM enhancement stories** table).
- **FR33–FR35** are explicitly **out of MVP** and listed under Roadmap.

### Architecture compliance

- **Epic 1 Story 1.1** establishes the **uv / Python 3.12** baseline per architecture.
- **Tables/entities** are introduced **when needed**: Story 1.2 adds run/stage persistence; later stories extend behavior without a “big bang” schema dump.
- **Starter template** requirement satisfied by Story 1.1.

### Story quality

- Stories are **sized for a single implementation increment**; dependencies flow **forward** only within each epic.
- **Epics are user-value oriented** (operators, scientists, marketing, admins) rather than pure technical layers.

### Epic independence

- **Epic 1** stands alone (stub pipeline).
- **Epics 3–5** replace stubs but depend on **Epic 1** handoff contracts.
- **Epic 6** depends on **3–5** outputs; **Epic 7** depends on **Epic 6**; **Epic 8** can be implemented in parallel with early epics for config consumed by **3–5**, but **full integration** requires **Epic 1** configuration loading—sequencing **Epic 8 early** is recommended for TA/watchlist before live agents.

### Dependency note (ordering recommendation)

Recommended implementation order: **Epic 1 → Epic 8 (config) in parallel with Epic 2 → Epics 3, 4, 5 (can parallelize after contracts) → Epic 6 → Epic 7**.

**GPT extension order (after baseline MVP):** shared OpenAI client → **3.3, 4.4, 5.4** (parallel) → **6.5** → **7.6**.

---

**Workflow status:** `bmad-create-epics-and-stories` **complete**. Next: **[IR] Check Implementation Readiness** (`bmad-check-implementation-readiness`), **[SP] Sprint Planning** (`bmad-sprint-planning`), or **`bmad-help`** ([BH]) for routing.
