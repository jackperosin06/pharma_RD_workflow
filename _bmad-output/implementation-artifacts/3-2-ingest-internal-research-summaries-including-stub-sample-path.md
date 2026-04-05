# Story 3.2: Ingest internal research summaries (including stub/sample path)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **internal research summaries merged when configured**,
so that **practice mode can use sample data** without live internal systems (FR7).

## Acceptance Criteria

1. **Given** a configured path or stub for internal research artifacts  
   **When** the Clinical stage runs  
   **Then** structured output incorporates **internal research** content when present  
   **And** when not configured, the stage still succeeds with **explicit “not configured”** in output (NFR-I1)

## Tasks / Subtasks

- [x] **Configuration (AC: 1, NFR-I1)** — Add settings in `pharma_rd/config.py` (via `get_settings()` only):
  - e.g. **`PHARMA_RD_INTERNAL_RESEARCH_PATH`**: optional **directory** or **single file** path (resolve relative to process cwd unless absolute); empty/unset means “not configured.”
  - Document in **`README.md`** and **`pharma_rd/.env.example`**; no secrets in repo (NFR-S1).

- [x] **Contract (AC: 1)** — Extend **`ClinicalOutput`** in `pharma_rd/pipeline/contracts.py`:
  - Add a structured list for internal summaries (e.g. **`InternalResearchItem`** with **`title`**, **`summary`**, **`reference`** or **`source_label`** — stable strings suitable for downstream synthesis).
  - Prefer **additive** fields with safe defaults so existing **schema_version 2** artifacts remain readable **or** bump **`schema_version`** with explicit migration notes in story completion — pick one approach and update **`tests/pipeline/test_contracts.py`** round-trip.
  - Keep **`extra="forbid"`**.

- [x] **Loader (AC: 1)** — Implement ingestion in **`pharma_rd/agents/`** and/or **`pharma_rd/integrations/`** (thin module):
  - Support **JSON** files (document exact schema — e.g. one object per file or array in one file); MVP may **glob** `*.json` under a directory.
  - **Stub/sample path:** add **`tests/fixtures/`** (or `pharma_rd/tests/fixtures/`) with **committed** minimal sample JSON for CI and practice demos.
  - On **missing directory**, **permission errors**, or **parse errors**: stage **still completes**; record issues in **`data_gaps`** / **`integration_notes`** (NFR-I1), not uncaught exceptions (unless invariant violated).

- [x] **Clinical agent merge (AC: 1)** — Update **`pharma_rd/agents/clinical.py`**:
  - After **PubMed** work from story **3.1**, merge **internal research** items into **`ClinicalOutput`** when configured and readable.
  - When **not configured**: set explicit wording in **`integration_notes`** and/or **`data_gaps`** such that operators see **“internal research not configured”** (not silent omission).
  - Preserve **`ensure_connector_probe("clinical")`**, **`run_clinical(run_id)`** signature, and existing **`clinical_publications`** logging semantics; add a concise structured log event if useful (e.g. internal item count), without breaking pipeline tests.

- [x] **Tests** — **`tests/agents/test_clinical.py`** (and loader unit tests if split):
  - Not configured → **`ClinicalOutput`** contains explicit not-configured messaging; stage would not raise.
  - Configured + valid fixtures → items appear in output.
  - Malformed / empty directory → NFR-I1 degradation paths; no crash.
  - Full **`pytest`** + **`ruff`** green.

- [x] **Docs** — **`README.md`**: internal research path, JSON shape, practice mode using bundled fixture path in tests.

## Dev Notes

### Epic context (Epic 3)

[Source: `_bmad-output/planning-artifacts/epics.md` — Epic 3, Story 3.2]

- **FR7:** Ingest **internal research summaries** when supplied via configured inputs (including **stub/sample** for practice).
- **NFR-I1:** Degrade gracefully — **not configured** must be explicit; partial/malformed inputs transparent.

### Scope boundaries

| In scope | Out of scope |
|----------|----------------|
| File-based **internal research** ingestion into **`ClinicalOutput`** | Live enterprise document stores, SSO-gated shares (later) |
| **Stub/sample** committed fixtures | Full Epic 8 configuration UI |
| Merge with **3.1** PubMed output | Competitor/consumer agents |

### Architecture compliance

[Source: `_bmad-output/planning-artifacts/architecture.md`]

| Topic | Requirement |
|-------|-------------|
| **Agents** | Clinical agent returns **Pydantic** only; **no** direct SQLite |
| **Config** | Central **`config.py`** + **`get_settings()`** |
| **Filesystem** | Read-only ingestion from configured path; validate paths defensively (**path traversal** / symlink surprises — reject or document MVP behavior) |

### Technical requirements

1. **Reuse** patterns from story **3.1**: `get_settings()`, `ClinicalOutput` lists, `data_gaps` / `integration_notes` for transparency.

2. **Downstream:** **`competitor.run_competitor`** may still ignore extended fields; **`Synthesis`** will eventually consume clinical JSON — use **clear, stable field names**.

3. **Security (NFR-S4):** Assume **no PHI** in MVP fixtures; do not log file bodies at INFO; keep summaries short in logs.

4. **Idempotency:** Same **`run_id`** semantics as today — ingestion is a function of config + files at run time.

### Project structure notes

- **`pharma_rd/agents/clinical.py`** — orchestration
- **`pharma_rd/pipeline/contracts.py`** — models
- **`pharma_rd/integrations/`** or **`pharma_rd/agents/internal_research.py`** — loader (match project style)
- **`tests/fixtures/`** — sample JSON

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 3.2]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR7, NFR-I1]
- [Source: `pharma_rd/agents/clinical.py` — current clinical stage]
- [Source: `pharma_rd/pipeline/contracts.py` — `ClinicalOutput`]
- [Source: `_bmad-output/implementation-artifacts/3-1-discover-and-summarize-clinical-trial-publications-for-configured-tas.md` — prior epic 3 story]

## Previous story intelligence

[Source: `_bmad-output/implementation-artifacts/3-1-discover-and-summarize-clinical-trial-publications-for-configured-tas.md`]

- **3.1** established **PubMed** path, **`ClinicalOutput` v2**, **`clinical_publications`** logging, **`get_settings` cache** cleared in **`tests/conftest.py`**.
- **Do not regress** PubMed behavior when internal research is disabled.
- **Connector probe** runs before agent logic — keep ordering consistent.

## Git intelligence

- Follow **`uv`**, **`ruff`**, **`pytest`** conventions in **`pharma_rd/README.md`**.

## Latest technical notes

- Prefer **UTF-8** text reads; bounded file size for MVP (optional max bytes in settings or hard cap with **`data_gaps`** note).

## Project context reference

- No **`project-context.md`** in repo.

## Dev Agent Record

### Agent Model Used

Cursor (GPT-5.1)

### Debug Log References

### Completion Notes List

- **`InternalResearchItem`** + **`internal_research_items`** on **`ClinicalOutput`** (additive **`schema_version` 2** defaults).
- **`pharma_rd/integrations/internal_research.py`**: `ingest_internal_research(settings)`; JSON object or array; directory `*.json`; NFR-I1 gaps for missing path, I/O, parse, oversize files.
- **`clinical.py`**: PubMed base then **`_merge_internal_research`**; log event **`internal_research`** with **`internal_research_count`**.
- Fixture: **`tests/fixtures/internal_research/sample.json`**; tests in **`tests/integrations/test_internal_research.py`** and **`tests/agents/test_clinical.py`**; **`test_logging`** expects **`internal_research`** event.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/clinical.py`
- `pharma_rd/pharma_rd/integrations/internal_research.py`
- `pharma_rd/tests/fixtures/internal_research/sample.json`
- `pharma_rd/tests/integrations/test_internal_research.py`
- `pharma_rd/tests/agents/test_clinical.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`

### Change Log

- 2026-04-06: Story 3.2 implementation — internal research JSON ingestion, clinical merge, tests, docs.

### Review Findings

- [x] [Review][Decision] Path resolution and symlink policy for `PHARMA_RD_INTERNAL_RESEARCH_PATH` — Resolved **2026-04-05**: **(A) document only** — MVP symlink and trust boundary described in `README.md`.

- [x] [Review][Patch] Align `source_label` fallback with contract default — [`pharma_rd/pharma_rd/integrations/internal_research.py:33-34`]

- [x] [Review][Patch] Add brief clinical artifact migration note — [`pharma_rd/README.md`]

- [x] [Review][Patch] Strengthen `test_run_clinical_no_ta_configured` — [`pharma_rd/tests/agents/test_clinical.py:28-29`]

- [x] [Review][Patch] Remove redundant `get_settings.cache_clear()` — [`pharma_rd/tests/agents/test_clinical.py`]

- [x] [Review][Defer] Unbounded `*.json` count per directory — A directory with very many JSON files could slow the clinical stage or use large memory; per-file byte cap exists but not a file-count cap. [`pharma_rd/pharma_rd/integrations/internal_research.py:122-138`] — deferred, pre-existing hardening gap for a future story.

- [x] [Review][Defer] PubMed `ConnectorFailure` still fails the clinical stage — Internal research degrades gracefully, but configured TA + live PubMed errors still raise through the runner (stage `failed`). Story 3.2 asks not to regress PubMed; broader NFR-I1 “complete with gaps” for HTTP outages may be a separate epic follow-up. [`pharma_rd/pharma_rd/agents/clinical.py`, `pharma_rd/pharma_rd/pipeline/runner.py`] — deferred, pre-existing behavior from Epic 3 PubMed path.

---

**Story completion status:** **done** — code review complete 2026-04-05 (decision + patches applied).
