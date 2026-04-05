# Story 4.1: Track approvals and regulatory disclosures

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **competitor approvals and material regulatory disclosures tracked** for configured competitors,
so that **we do not miss competitive regulatory moves** (FR8).

## Acceptance Criteria

1. **Given** competitor watchlist configuration  
   **When** the Competitor stage runs  
   **Then** structured output lists **approvals** and **disclosures** found in the observation window with **sources**  
   **And** integration failures are **classified** in logs (NFR-I2)

## Tasks / Subtasks

- [x] **Configuration (AC: 1, NFR-I2)** — Extend `pharma_rd/config.py` (via `get_settings()` only): **`PHARMA_RD_COMPETITOR_WATCHLIST`**, **`PHARMA_RD_COMPETITOR_OBSERVATION_DAYS`**, **`PHARMA_RD_COMPETITOR_REGULATORY_PATH`**, **`PHARMA_RD_COMPETITOR_REGULATORY_MAX_FILE_BYTES`**, **`PHARMA_RD_OPENFDA_DRUGSFDA_URL`**, **`PHARMA_RD_OPENFDA_MAX_RESULTS`**. Document in **`README.md`** and **`pharma_rd/.env.example`**.

- [x] **Contract (AC: 1)** — Extend **`CompetitorOutput`** in `pharma_rd/pipeline/contracts.py`: **`RegulatoryApprovalItem`**, **`RegulatoryDisclosureItem`**, **`schema_version` 2**, **`run_id`**, lists + gaps + notes; update **`tests/pipeline/test_contracts.py`**.

- [x] **Integration layer (AC: 1, NFR-I2)** — **`pharma_rd/integrations/regulatory_signals.py`**: fixture loader + **`fetch_openfda_approvals`** via **`request_with_retries`**.

- [x] **Competitor agent (AC: 1)** — **`pharma_rd/agents/competitor.py`**: **`ensure_connector_probe`**, merge fixture and/or OpenFDA; log **`competitor_regulatory`**.

- [x] **Tests** — **`tests/agents/test_competitor.py`**, **`tests/integrations/test_regulatory_signals.py`**, **`test_logging`**, **`test_runner_resume`**, **`test_config`**.

- [x] **Docs** — **`README.md`**: competitor stage, schema v2, observation window (calendar days), fixture JSON shape.

## Dev Notes

### Epic context (Epic 4)

[Source: `_bmad-output/planning-artifacts/epics.md` — Epic 4]

- **FR8:** Track **competitor product approvals** and material **regulatory disclosures** for configured competitors.
- **FR9 / FR10:** Covered by **4.2** and **4.3** — do **not** implement pipeline-only or patent-specific scopes in this story unless needed to avoid duplicate models; prefer leaving extension points (extra optional lists or TODO in `integration_notes`) over scope creep.

### Scope boundaries

| In scope | Out of scope |
|----------|--------------|
| **Approvals** + **material disclosures** lists with **sources** and observation window | Full **Epic 8** configuration UI; rich **watchlist** schema (**8.2**) beyond comma-separated MVP env |
| **NFR-I2** classification via existing **`ConnectorFailure`** / **`IntegrationErrorClass`** | New observability stack; non-HTTP integrations |
| **`CompetitorOutput` v2** + competitor agent + tests | **Consumer** / **Synthesis** consumption of new fields (may ignore until Epic 6) |

### Architecture compliance

[Source: `_bmad-output/planning-artifacts/architecture.md`]

| Topic | Requirement |
|-------|-------------|
| **Agents** | Competitor agent returns **Pydantic** only; **no** direct SQLite |
| **Config** | **`config.py`** + **`get_settings()`**; no scattered `os.environ` |
| **HTTP** | **`httpx`** via **`request_with_retries`**; timeouts/retries aligned with Epic 2 |
| **Logs** | Structured JSON; **`run_id`**, **`stage`**, **`agent`**; **`integration_error_class`** on connector failures |

### Technical requirements

1. **Reuse** clinical patterns: **`get_settings()`**, list-based artifacts, **`data_gaps`** / **`integration_notes`**, explicit “not configured” semantics.
2. **Clinical handoff:** **`run_competitor(run_id, clinical)`** receives **`ClinicalOutput`** — use only if helpful for cross-checking TA/competitor overlap; otherwise avoid unnecessary coupling.
3. **Security:** No PHI in fixtures; short summaries in logs at INFO.

### Project structure notes

- **`pharma_rd/agents/competitor.py`** — orchestration
- **`pharma_rd/pipeline/contracts.py`** — **`CompetitorOutput`** models
- **`pharma_rd/integrations/`** — regulatory / OpenFDA or file loader
- **`tests/fixtures/`** — sample JSON

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.1]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR8, NFR-I2]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Implementation patterns]
- [Source: `pharma_rd/agents/clinical.py` — logging and NFR-I1 patterns]
- [Source: `pharma_rd/http_client.py` — `ConnectorFailure`, `IntegrationErrorClass`]

## Previous story intelligence

[Source: `_bmad-output/implementation-artifacts/3-2-ingest-internal-research-summaries-including-stub-sample-path.md`]

- **3.2** established **internal research** JSON ingestion, **`ClinicalOutput`** schema_version **2**, **`get_settings` cache** cleared in **`tests/conftest.py`**, and README migration notes for schema bumps.
- Apply the same rigor for **`CompetitorOutput`** versioning and **`pytest`** + **`ruff`** gates.

## Git intelligence

- Repo history is sparse in this workspace clone; follow **`uv`**, **`ruff`**, **`pytest`** in **`pharma_rd/README.md`** and existing agent modules.

## Latest technical notes

- If using **OpenFDA** or similar public APIs: **HTTPS** (NFR-S3 baseline); respect rate limits; mock in tests. Check current API docs for query parameters and response shape before locking types.

## Project context reference

- No **`project-context.md`** in repo.

## Dev Agent Record

### Agent Model Used

Cursor (GPT-5.1)

### Debug Log References

### Completion Notes List

- **`CompetitorOutput` v2** with **`RegulatoryApprovalItem`** / **`RegulatoryDisclosureItem`**; **`run_id`**, **`approval_items`**, **`disclosure_items`**, **`data_gaps`**, **`integration_notes`**.
- **Config:** `PHARMA_RD_COMPETITOR_WATCHLIST`, `PHARMA_RD_COMPETITOR_OBSERVATION_DAYS`, `PHARMA_RD_COMPETITOR_REGULATORY_PATH`, `PHARMA_RD_COMPETITOR_REGULATORY_MAX_FILE_BYTES`, `PHARMA_RD_OPENFDA_DRUGSFDA_URL`, `PHARMA_RD_OPENFDA_MAX_RESULTS`.
- **`pharma_rd/integrations/regulatory_signals.py`**: fixture JSON (`approvals` / `disclosures` arrays); **`fetch_openfda_approvals`** via **`request_with_retries`** (NFR-I2).
- **`competitor.py`**: fixture path takes precedence over live OpenFDA; log event **`competitor_regulatory`** with counts.
- Fixture **`tests/fixtures/competitor_regulatory/sample.json`**; tests in **`tests/agents/test_competitor.py`**, **`tests/integrations/test_regulatory_signals.py`**; **`test_logging`** expects **`competitor_regulatory`**; stub count 3.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/competitor.py`
- `pharma_rd/pharma_rd/integrations/regulatory_signals.py`
- `pharma_rd/tests/fixtures/competitor_regulatory/sample.json`
- `pharma_rd/tests/agents/test_competitor.py`
- `pharma_rd/tests/integrations/test_regulatory_signals.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/tests/pipeline/test_runner_resume.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`

### Change Log

- 2026-04-05: Story file created — ultimate context engine analysis completed - comprehensive developer guide created
- 2026-04-05: Story 4.1 implementation — competitor regulatory fixtures, OpenFDA drugsfda client, CompetitorOutput v2, tests, docs.
- 2026-04-05: Code review — decision (B) + patches applied; story marked **done**.

### Review Findings

- [x] [Review][Decision] **Observation window vs AC** — Resolved **2026-04-05**: **(B) document-only MVP** — README states the observation window is **narrative**; rows are **not** filtered by **`observed_at`** vs rolling window until a future story.

- [x] [Review][Patch] **`observed_at` for OpenFDA-derived items** — Implemented **`submission_status_date`** parsing (YYYYMMDD / ISO) with **`data_gaps`** when placeholder epoch used. [`pharma_rd/pharma_rd/integrations/regulatory_signals.py`]

- [x] [Review][Patch] **List types in competitor agent** — **`list[RegulatoryApprovalItem]`** / **`list[RegulatoryDisclosureItem]`**. [`pharma_rd/pharma_rd/agents/competitor.py`]

- [x] [Review][Patch] **README: observation window + trust boundary** — Narrative-window MVP + competitor path security note. [`pharma_rd/README.md`]

- [x] [Review][Defer] **Unbounded `*.json` under competitor fixture directory** — Same class of issue as internal research: many files could slow the stage. [`pharma_rd/pharma_rd/integrations/regulatory_signals.py:174-191`] — deferred, pre-existing hardening pattern.

- [x] [Review][Defer] **OpenFDA `drugsfda` field drift** — **`application_number`**, **`sponsor_name`**, and **`products`** shapes depend on API responses; if the live schema differs, titles/references may degrade silently. Add a periodic integration check or manual validation against OpenFDA docs in a future story. [`pharma_rd/pharma_rd/integrations/regulatory_signals.py:206-245`] — deferred, pre-existing integration risk.

---

**Story completion status:** **done** — code review complete 2026-04-05.
