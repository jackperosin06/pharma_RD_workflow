# Story 2.2: Per-stage timeouts and bounded retries for external calls

Status: done

<!-- Optional: run Validate Story ([VS]) before dev-story for a quality check. -->

## Story

As a **workflow operator**,
I want **external calls to time out and retry within bounds**,
so that **one slow source cannot hang the entire run invisibly** (NFR-P3, NFR-P1).

## Acceptance criteria

1. **Given** connector HTTP calls use shared client settings
   **When** a source exceeds the configured timeout or returns transient errors
   **Then** retries occur up to a **bounded** count with backoff
   **And** failure after retries marks the stage **failed** with an **actionable** message (NFR-R1) and **classified** reason where possible (NFR-I2)

## Tasks / subtasks

- [x] **Settings & shared HTTP client (AC: 1)** — Extend **`Settings`** in **`pharma_rd/config.py`** with **`PHARMA_RD_`**-prefixed env fields:
  - **`http_timeout_seconds`** (request timeout for connector calls; sensible default)
  - **`http_max_retries`** (bounded count; **0** means no retries)
  - **`http_retry_backoff_seconds`** (base backoff; **exponential** between attempts)
  - **`connector_probe_url`** (optional **URL**; when set, each pipeline stage performs a minimal **GET** through the shared client so connector behavior is exercised end-to-end; when unset, stages skip the probe and remain stub-only)
  - Document in **`.env.example`** and **`README.md`**.

- [x] **`pharma_rd/http_client.py` (AC: 1)** — Implement **`request_with_retries`** using **`httpx`** and **`get_settings()`**:
  - Per-request **timeout** from settings
  - Retry only **transient** conditions: timeouts, connection errors, **429**, **502**, **503**, **504** (document; do not retry arbitrary 4xx)
  - **Bounded** retries + **exponential backoff** from base
  - Structured logs for retry attempts (**`event`** e.g. **`connector_retry`**) with attempt / max / backoff — no secrets in logs
  - Raise **`ConnectorFailure`** (or equivalent) carrying an **actionable** message and **`IntegrationErrorClass`** (or similar enum) for **timeout** / **transient_exhausted** / **http_client_error** / etc.

- [x] **Agent wiring (AC: 1)** — Each stage agent calls **`ensure_connector_probe(stage_key)`** (or equivalent) before existing stub logic when **`connector_probe_url`** is set; shared client only.

- [x] **Runner / observability (AC: 1)** — On connector failure, persist **error_summary** that includes classification; emit structured log field **`integration_error_class`** when present (extend **`JsonLineFormatter`** allowlist if needed).

- [x] **Tests (AC: 1)** — **`tests/test_http_client.py`**: **`httpx.MockTransport`** (or injectable client) for timeout, transient 503 then success, retries exhausted, non-retryable 4xx. Pipeline tests remain fast with **probe disabled** (default); add at least one test path with probe enabled and mocked transport if feasible.

### Review Findings

- [x] [Review][Patch] Remove dead enum member **`IntegrationErrorClass.UNKNOWN`** or assign it from a genuine fallback path [`pharma_rd/http_client.py` ~26] — **fixed:** removed **`UNKNOWN`**
- [x] [Review][Defer] Add **jitter** to exponential backoff on HTTP retries (reduce synchronized retry storms) — deferred; not required by AC

## Dev notes

### Epic context (Epic 2)

[Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.2]

**Out of scope:** Story **2.3** (retry failed stage without re-running upstream) — do not implement partial graph replay here.

### Architecture compliance

| Topic | Requirement |
|-------|-------------|
| HTTP | **`httpx`** already in project; no new HTTP stack unless justified |
| Config | **`pydantic-settings`**, **`PHARMA_RD_`** prefix |
| Logging | Structured JSON; **failure classification** (NFR-I2) |

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 2.2]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — integrations, observability]

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

### Completion Notes List

- Added **`pharma_rd/http_client.py`**: **`request_with_retries`**, **`ConnectorFailure`**, **`IntegrationErrorClass`** ( **`StrEnum`** ); retries on timeout, connection errors, HTTP **429 / 500 / 502 / 503 / 504**; exponential backoff; **`connector_retry`** logs.
- **`pharma_rd/agents/connector_probe.py`**: **`ensure_connector_probe`**; all five agents call it before stub logic.
- **`Settings`**: **`http_timeout_seconds`**, **`http_max_retries`**, **`http_retry_backoff_seconds`**, **`connector_probe_url`** (empty/whitespace → **None**).
- **`runner`**: **`integration_error_class`** on **`stage_failed`** logs for **`ConnectorFailure`**; **`error_summary`** includes **`[classification]`**.
- **`JsonLineFormatter`**: optional **`integration_error_class`**, retry-related fields.
- Tests: **`tests/test_http_client.py`**, **`test_runner`** (classification + probe wiring), **`test_config`** (probe URL empty).

### Implementation Plan

Settings → **`http_client`** → **`connector_probe`** in agents → runner/logging → tests → README / `.env.example`.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/http_client.py`
- `pharma_rd/pharma_rd/agents/connector_probe.py`
- `pharma_rd/pharma_rd/agents/clinical.py`
- `pharma_rd/pharma_rd/agents/competitor.py`
- `pharma_rd/pharma_rd/agents/consumer.py`
- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/test_http_client.py`
- `pharma_rd/tests/pipeline/test_runner.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/2-2-per-stage-timeouts-and-bounded-retries-for-external-calls.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change log

- 2026-04-05: Story created for dev-story **2-2**; status **in-progress**.
- 2026-04-05: Implemented shared HTTP client, agent probe wiring, tests, docs; status **review**.
- 2026-04-05: Code review — Review Findings appended; status **in-progress** (open patch items).
- 2026-04-05: Code review patches applied (`UNKNOWN` removed); status **done**.
