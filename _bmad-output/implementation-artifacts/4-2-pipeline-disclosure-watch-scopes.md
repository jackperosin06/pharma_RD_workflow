# Story 4.2: Pipeline disclosure watch scopes

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **pipeline disclosures captured for configured watch scopes**,
so that **we see pipeline-relevant competitor activity** (FR9).

## Acceptance Criteria

1. **Given** watch scopes in configuration  
   **When** the Competitor stage runs  
   **Then** output includes **pipeline disclosure** items matching scope or explicitly states **none found**  
   **And** partial data paths remain **transparent** in output (NFR-I1)

## Tasks / Subtasks

- [x] **Configuration (AC: 1, NFR-I1)** — Extend `pharma_rd/config.py` (via `get_settings()` only): add **`PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES`** (or equivalent name aligned with existing `Field` naming) — comma-separated **watch scope** labels/keywords for FR9. Empty = not configured (explicit gaps/notes, stage still succeeds). Document in **`README.md`** and **`pharma_rd/.env.example`**. Add validator/helper mirroring `competitor_labels()` / `therapeutic_area_labels()` (e.g. `pipeline_disclosure_scope_labels()`).

- [x] **Contract (AC: 1)** — Extend **`CompetitorOutput`** in `pharma_rd/pipeline/contracts.py`:
  - New model **`PipelineDisclosureItem`** (distinct from **`RegulatoryDisclosureItem`** — FR8 vs FR9): at minimum `title`, `summary`, `reference`, `observed_at`, `source_label`, and a field tying the row to scope (e.g. **`matched_scope`** or **`watch_scope`**) so operators see *why* it matched.
  - Add **`pipeline_disclosure_items: list[PipelineDisclosureItem]`** (default factory empty).
  - Bump **`schema_version`** if the project convention requires it when adding a new top-level list (follow **`4-1`** / Clinical precedent; if additive-only default-empty lists stay on v2, document the choice in dev notes).
  - Update **`tests/pipeline/test_contracts.py`** for serialization and validation.

- [x] **Data path (AC: 1, NFR-I1)** — Implement ingestion consistent with **`regulatory_signals.py`** patterns:
  - **Preferred MVP:** extend competitor regulatory **fixture JSON** (same directory/file as **`4-1`** or a dedicated optional path) with a **`pipeline_disclosures`** array (or separate file keyed by path — document shape in README). Each entry should carry **scope tags** so the agent can **filter** to configured watch scopes.
  - When scopes are configured but **no** pipeline rows match: **`pipeline_disclosure_items`** is empty **and** **`integration_notes`** or **`data_gaps`** explicitly states **none found** for the configured scopes (not silent empty).
  - When a fixture file is **partially** readable (skipped files, size limits, parse warnings): surface in **`data_gaps`** / **`integration_notes`** per NFR-I1 (reuse clinical/competitor wording patterns).

- [x] **Competitor agent (AC: 1)** — **`pharma_rd/agents/competitor.py`**:
  - After existing FR8 regulatory merge, compute **FR9 pipeline disclosures**: filter/tag by **`pipeline_disclosure_scope_labels()`** vs ingested rows.
  - Structured log event: extend or add alongside **`competitor_regulatory`** (e.g. **`competitor_pipeline_disclosures`**) with counts and outcome — update **`tests/pipeline/test_logging.py`** expectations accordingly.

- [x] **Tests** — **`tests/agents/test_competitor.py`**: cases for (a) scopes unset → explicit not-configured semantics without breaking FR8; (b) scopes set + fixture with matching rows → non-empty **`pipeline_disclosure_items`**; (c) scopes set + no matching rows → empty list + explicit “none found” wording; (d) partial fixture transparency if implemented. Add/extend **`tests/fixtures/`** JSON. **`tests/test_config.py`** for new settings.

- [x] **Docs** — **`README.md`**: FR9 slice, fixture schema snippet, distinction **FR8 regulatory disclosures** vs **FR9 pipeline disclosures**.

## Dev Notes

### Epic context (Epic 4)

[Source: `_bmad-output/planning-artifacts/epics.md` — Stories 4.1–4.3]

| Story | Focus |
|-------|--------|
| **4.1** | FR8 — **approvals** + **material regulatory disclosures** (`approval_items`, `disclosure_items`) |
| **4.2 (this)** | FR9 — **pipeline disclosures** scoped by configuration (**watch scopes**) — **separate** list/model |
| **4.3** | FR10 — patent filing flags (do not implement here) |

**Scope boundaries:** Do not conflate **`RegulatoryDisclosureItem`** with **`PipelineDisclosureItem`**. If reuse of fixture files is convenient, use **distinct JSON keys** and models so FR8 and FR9 evolve independently.

### PRD alignment

[Source: `_bmad-output/planning-artifacts/prd.md`]

- **FR9:** Competitor Intelligence Agent tracks **pipeline disclosures** relevant to configured **watch scopes**.
- **NFR-I1:** Connectors declare expected behavior; **empty/partial** data must be **transparent** in output (lists + notes/gaps), not silent success with hidden omissions.

### Architecture compliance

[Source: `_bmad-output/planning-artifacts/architecture.md`]

| Topic | Requirement |
|-------|-------------|
| **Agents** | Competitor agent returns **Pydantic** contracts only; **no** direct SQLite in agent |
| **Config** | Central **`config.py`** + **`get_settings()`**; no scattered `os.environ` |
| **HTTP** | If any live fetch is added: **`httpx`** via **`request_with_retries`**; failures classified (**NFR-I2**) — fixture-first tests |
| **Logs** | Structured JSON; **`run_id`**, **`stage`**, **`agent`**; meaningful **`event`** names |

### Technical requirements

1. **Reuse** patterns from **`4-1`**: `get_settings().cache_clear()` in tests, list-based `data_gaps` / `integration_notes`, explicit “not configured” semantics.
2. **Non-goals for this story:** Epic **8** full configuration UI; live patent feeds (**4.3**); Synthesis consumption (**Epic 6**).
3. **Security:** No PHI in fixtures; keep summaries in logs at INFO.

### Project structure notes

| Area | Path |
|------|------|
| Agent | `pharma_rd/agents/competitor.py` |
| Contracts | `pharma_rd/pipeline/contracts.py` |
| Integrations | `pharma_rd/integrations/regulatory_signals.py` (extend) or `pharma_rd/integrations/pipeline_disclosures.py` if split improves clarity |
| Tests | `tests/agents/`, `tests/pipeline/`, `tests/fixtures/` |

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 4.2]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR9, NFR-I1]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — agents, config, integrations]
- [Source: `pharma_rd/agents/competitor.py` — FR8 flow to extend]
- [Source: `pharma_rd/integrations/regulatory_signals.py` — fixture parsing, OpenFDA]
- [Source: `_bmad-output/implementation-artifacts/4-1-track-approvals-and-regulatory-disclosures.md` — completed patterns and file list]

## Previous story intelligence

[Source: `_bmad-output/implementation-artifacts/4-1-track-approvals-and-regulatory-disclosures.md`]

- **`CompetitorOutput` v2** with **`RegulatoryApprovalItem`** / **`RegulatoryDisclosureItem`**; fixture path **`PHARMA_RD_COMPETITOR_REGULATORY_PATH`**; OpenFDA via **`fetch_openfda_approvals`**.
- Log event **`competitor_regulatory`**; **`test_logging`** asserts it.
- **Code review:** observation window is **narrative MVP** (README); list types must be explicit; **`data_gaps`** when dates missing.
- **Extend** rather than fork: add FR9 fields and tests alongside FR8.

## Git intelligence

[Source: `git log` — workspace]

- Recent commits are high-level epic batches; follow **`README.md`** for **`uv`**, **`ruff`**, **`pytest`**.

## Latest technical notes

- No mandatory new public API for MVP if fixture-driven; if researching CDER/SEC/company pipeline sources later, pin docs and keep tests offline.

## Project context reference

- No **`project-context.md`** in repo; use this story + **`4-1`** + epics/PRD.

## Dev Agent Record

### Agent Model Used

GPT-5.1 (Cursor)

### Debug Log References

### Completion Notes List

- Implemented **`PHARMA_RD_PIPELINE_DISCLOSURE_SCOPES`** and **`pipeline_disclosure_scope_labels()`**; **`PipelineDisclosureItem`** + **`CompetitorOutput.schema_version` 3** with **`pipeline_disclosure_items`**.
- Extended regulatory JSON with **`pipeline_disclosures`** + **`scope_tags`**; **`filter_pipeline_disclosures`**; competitor supports **pipeline-only** runs (FR9 scopes + fixture without watchlist).
- Log event **`competitor_pipeline_disclosures`**; tests and README updated.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/competitor.py`
- `pharma_rd/pharma_rd/integrations/regulatory_signals.py`
- `pharma_rd/tests/agents/test_competitor.py`
- `pharma_rd/tests/integrations/test_regulatory_signals.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/tests/fixtures/competitor_regulatory/sample.json`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`

### Change Log

- 2026-04-05: Story 4.2 implemented — FR9 pipeline disclosures, config, contracts v3, tests, docs.
- 2026-04-05: Code review — clean; story marked **done**.

### Review Findings

- [x] [Review] **Clean review** — Blind / edge / acceptance layers: no blocking issues; optional directory `*.json` volume is the same deferred class as story 4-1 (`deferred-work.md`).

---

**Story completion status:** **done** — code review complete 2026-04-05.
