# Story 4.3: Patent filing flags

Status: done

## Story

As a **workflow operator**,
I want **significant patent filing activity flagged** for configured competitors,
so that **IP pressure is visible early** (FR10).

## Acceptance Criteria

1. **Given** configured competitors and keyword/patent feeds where available  
   **When** the Competitor stage runs  
   **Then** output includes **patent-related flags** with references or **explicit empty** state  
   **And** TLS used for external APIs where supported (NFR-S3)

## Tasks / Subtasks

- [x] **Contract** — `PatentFilingFlagItem`, `CompetitorOutput.schema_version` 4, `patent_filing_flags` list; tests in `test_contracts.py`.
- [x] **Fixture ingestion** — `patent_filing_flags` array in regulatory JSON; `competitor_tags` optional (empty = applies to first watchlist label); `filter_patent_filing_flags` in `regulatory_signals.py`.
- [x] **Competitor agent** — merge flags, NFR-I1 notes when no fixture / no matches; log `competitor_patent_flags`.
- [x] **Tests** — `test_competitor.py`, `test_logging.py`, `test_regulatory_signals.py`; extend `sample.json`.
- [x] **Docs** — README, `.env.example` (FR10 / TLS note for live APIs).

## Dev Agent Record

### Agent Model Used

GPT-5.1 (Cursor)

### Debug Log References

### Completion Notes List

- **`PatentFilingFlagItem`** + **`CompetitorOutput` v4** with **`patent_filing_flags`**.
- **`patent_filing_flags`** JSON array + **`filter_patent_filing_flags`**; early exit includes FR10 **`data_gaps`** line.
- Log **`competitor_patent_flags`**; **`test_logging`** asserts event.

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/integrations/regulatory_signals.py`
- `pharma_rd/pharma_rd/agents/competitor.py`
- `pharma_rd/tests/agents/test_competitor.py`
- `pharma_rd/tests/integrations/test_regulatory_signals.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/tests/fixtures/competitor_regulatory/sample.json`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`

### Change Log

- 2026-04-05: Story 4.3 implemented — FR10 patent filing flags, schema v4, tests, docs.

---

**Story completion status:** **done**

### Review Findings

- [x] [Review][Patch] Stale module docstring in `test_regulatory_signals.py` — file header still says “FR8” only; patent/FR10 coverage now lives in this module. [`pharma_rd/tests/integrations/test_regulatory_signals.py:1`]
- [x] [Review][Patch] No automated test for omitted `competitor_tags` on a `patent_filing_flags` row — README states omitted/empty tags map to the **first** watchlist label (MVP), but no test exercises that branch (only `competitor_tags: ["AcmePharma"]` in `sample.json`). [`pharma_rd/tests/agents/test_competitor.py` / `sample.json`]
- [x] [Review][Defer] Downstream stages still stub — `ConsumerOutput` / `SynthesisOutput` do not consume `patent_filing_flags` yet [`pharma_rd/pharma_rd/agents/consumer.py`] — deferred, pre-existing roadmap (later epics), not a defect in 4-3 implementation.
