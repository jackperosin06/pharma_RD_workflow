# Story 5.2: Pharmacy sales trend signals when configured

Status: done

## Story

As a **marketing lead**,
I want **pharmacy sales trends included when feeds exist**,
so that **commercial framing is grounded** where data allows (FR12).

## Acceptance Criteria

1. **Given** optional sales feed configuration  
   **When** feeds are **unavailable** or **empty**  
   **Then** the stage still completes with **transparent** explanation (NFR-I1)  
   **When** feeds return data  
   **Then** trends are summarized in structured output with **scope** stated

## Tasks / Subtasks

- [x] **Contract** — Extend `ConsumerOutput`: bump `schema_version` to **3**; add typed model(s) for pharmacy sales trend line items (e.g. summary text, **scope** label/region, optional period, source reference). Keep `extra="forbid"`. Update `tests/pipeline/test_contracts.py` round-trip.
- [x] **Configuration** — Add `PHARMA_RD_*` settings for optional sales feed (fixture path and/or URL base — follow existing fixture-first MVP pattern unless story dictates live HTTP). Document in `.env.example`; no secrets in repo (NFR-S1).
- [x] **Integration** — Add or extend `pharma_rd/integrations/` loader for sales JSON (bounded reads, clear gaps on parse/IO), aligned with `consumer_feedback.py` patterns.
- [x] **Agent** — Extend `run_consumer`: merge sales trends into output; when feed not configured, explicit note in `integration_notes` or `data_gaps` (NFR-I1); when configured but empty/unreadable, transparent explanation; when data present, populate trend list with **scope** field filled.
- [x] **Logging** — Structured log event for sales trend outcome (count/skipped) consistent with `consumer_feedback` style.
- [x] **Tests** — Extend `tests/agents/test_consumer.py` (or split module if large): not configured, empty fixture, happy path with scope; contract tests for v3.
- [x] **Docs** — `README.md` and `.env.example` for FR12 env vars and schema v3.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| FR12 | Pharmacy sales trends when feeds exist; scope in output |
| NFR-I1 | Unavailable/empty → stage completes + transparency |
| NFR-S4 | Non-PHI MVP assumption for sales stubs |
| Prior | `ConsumerOutput` v2 (5.1) — extend additively; synthesis still stub |

### Architecture compliance

- **Settings:** `get_settings()` only; `PHARMA_RD_` prefix; empty string → `None` validators where paths are optional.
- **Observability:** JSON log lines; `run_id` via pipeline context; new `event` name distinct from `consumer_feedback`.
- **Handoff:** Consumer stage only; do not implement synthesis consumption of sales fields (Epic 6).

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Config | `pharma_rd/pharma_rd/config.py` |
| Agent | `pharma_rd/pharma_rd/agents/consumer.py` |
| Integration | `pharma_rd/pharma_rd/integrations/` (e.g. `pharmacy_sales.py` or extend existing) |
| Tests | `pharma_rd/tests/agents/test_consumer.py`, `pharma_rd/tests/pipeline/test_contracts.py`, `pharma_rd/tests/pipeline/test_logging.py` if new events |
| Fixtures | `pharma_rd/tests/fixtures/...` |
| Docs | `pharma_rd/README.md`, `pharma_rd/.env.example` |

### References

- Epic 5 / Story 5.2: `_bmad-output/planning-artifacts/epics.md`
- Story 5.1 artifact: `_bmad-output/implementation-artifacts/5-1-consumer-feedback-signals.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`ConsumerOutput` schema v3** with **`PharmacySalesTrendItem`** (`summary`, **`scope`**, optional **`period`**, **`source`**).
- **`integrations/pharmacy_sales.py`** — `pharmacy_sales_trends` fixture load; NFR-I1 gaps and empty-array transparency.
- **`consumer_pharmacy_sales`** log event with **`sales_trend_count`**; **`logging_setup`** extended.
- When sales path unset: **`integration_notes`** FR12 configuration hint; pipeline tests assert both consumer events.

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/agents/consumer.py`
- `pharma_rd/pharma_rd/integrations/pharmacy_sales.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_consumer.py`
- `pharma_rd/tests/fixtures/pharmacy_sales/sample.json`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Story 5.2 implemented — FR12 pharmacy sales trends, schema v3, tests, docs.
- 2026-04-05: Code review — `period` int/float coercion in `pharmacy_sales.py`; regression test.

### Review Findings

- [x] [Review][Patch] **`period` JSON typing** — [`pharma_rd/pharma_rd/integrations/pharmacy_sales.py`](pharma_rd/pharma_rd/integrations/pharmacy_sales.py) `_parse_trend_obj` drops non-string `period` values silently (e.g. numeric `2025`). Prefer coercing **`int`/`float`** to string for display, with an explicit **`bool` exclusion** (`bool` is a `int` subclass in Python—avoid treating `true`/`false` as years). **Resolved:** numeric `period` coerced to string; `test_pharmacy_sales_period_numeric_coerced`.

- [x] [Review][Defer] **`_resolve_config_path` duplication** — [`pharma_rd/pharma_rd/integrations/pharmacy_sales.py:12`] — same helper as `consumer_feedback` / `regulatory_signals`; consolidate in a shared module when touching integrations.

- [x] [Review][Defer] **Large bundled working tree** — Diff includes Epic 5.1 + 5.2 and incidental `test_competitor` docstring edit; prefer story-scoped commits for easier review next time.

---

**Story completion status:** done — Review patch applied; defers recorded in `deferred-work.md`.
