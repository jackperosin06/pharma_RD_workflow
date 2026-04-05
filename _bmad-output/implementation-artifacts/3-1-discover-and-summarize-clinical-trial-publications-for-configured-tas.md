# Story 3.1: Discover and summarize clinical trial publications for configured TAs

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **the Clinical agent to discover and summarize relevant clinical trial publications**,
so that **R&D sees up-to-date trial signal** for configured therapeutic areas (FR6).

## Acceptance Criteria

1. **Given** TA scope from configuration (FR23 / Epic 8 alignment)
   **When** the Clinical stage runs for a **run_id**
   **Then** output includes **summaries** of new or updated **trial publications** relevant to the TA with **references** suitable for human follow-up
   **And** empty or partial source data degrades per **NFR-I1** with explicit notes in structured output

## Tasks / Subtasks

- [x] **Therapeutic area scope (AC: 1)** — Expose **configured TA scope** to the Clinical agent without waiting for full Epic 8 UX:
  - Add **minimal** settings in `pharma_rd/config.py` (e.g. comma-separated `PHARMA_RD_THERAPEUTIC_AREAS` or a small JSON/list field) so operators can set scope via **environment** (FR23 slice for MVP pipeline).
  - Document in **`README.md`** + **`.env.example`**; keep defaults safe for CI/offline (e.g. empty list → explicit “no TA configured” in output per NFR-I1, not a hard crash).

- [x] **Structured contract (AC: 1, NFR-I1)** — Evolve **`ClinicalOutput`** in `pharma_rd/pipeline/contracts.py`:
  - Replace stub-only shape with fields that carry **publication summaries**, **references** (URLs, PMIDs, NCT IDs, or stable citation strings—pick one consistent scheme and document it), **`run_id` echo or correlation** if useful for audit, and **`integration_notes` / `data_gaps`** lists for **NFR-I1** transparency.
  - Bump **`schema_version`** if the JSON shape is not backward-compatible; update **`tests/pipeline/test_contracts.py`** round-trip expectations.
  - Keep **`extra="forbid"`** unless architecture explicitly relaxes it—list every field explicitly.

- [x] **Discovery + summarization (AC: 1)** — Implement real logic in **`pharma_rd/agents/clinical.py`** (and thin helpers under **`pharma_rd/integrations/`** if needed):
  - Use **public** APIs suitable for MVP (e.g. **PubMed E-utilities** for literature and/or **ClinicalTrials.gov API** for trial records)—call through existing **`pharma_rd.http_client`** (`httpx`) with timeouts/retries already from settings (story 2.2).
  - Map **TA labels** from settings to **queries** (document the mapping strategy: keyword expansion table vs raw query string—avoid silent overfitting).
  - Produce **short summaries** (template or lightweight extraction acceptable for MVP; must be deterministic enough to test with **recorded HTTP mocks**).

- [x] **Graceful degradation (AC: 1, NFR-I1)** — On empty results, rate limits, partial XML/JSON, or auth/network classification:
  - Stage **still completes** with **`ClinicalOutput`** that states what was attempted and what is missing; align with **`ConnectorFailure`** / **`integration_error_class`** patterns from story 2.2 where the failure is HTTP-level.
  - Do **not** fail the whole pipeline for “no new publications” if that is a valid outcome—distinguish **“no signal”** vs **“connector broken”** in structured fields and logs.

- [x] **Preserve pipeline integration** — Keep **`ensure_connector_probe("clinical")`** behavior unless product explicitly removes it; **`run_clinical(run_id)`** signature stays the entry point used by **`pharma_rd/pipeline/runner.py`**.

- [x] **Tests** — Add **`tests/agents/test_clinical.py`** (and optional **`tests/integrations/...`**) using **`httpx` mocking** or **`respx`** / `unittest.mock` to avoid live network in CI:
  - Happy path: mocked responses → expected summaries + references.
  - Empty/partial paths → NFR-I1 fields populated; no uncaught exceptions.
  - Contract JSON round-trip still passes for **`ClinicalOutput`**.

- [x] **Docs** — **`README.md`**: how to set TA scope, which external services are called, and practice/offline expectations.

### Review Findings

- [x] [Review][Decision] PubMed scope vs “clinical trial publications” — **Resolved (option B):** `build_pubmed_query` now ANDs **`Clinical Trial[Publication Type]`** with the TA **Title/Abstract** OR block so retrieved PubMed rows are trial-typed publications.

- [x] [Review][Patch] Harden `pubmed_search_pmids` for NCBI failure modes — **Resolved:** non-JSON esearch bodies and `ERROR` in `esearchresult` (or top-level) now raise **`ConnectorFailure`** with **`HTTP_CLIENT_ERROR`**; malformed `esearchresult` type is rejected explicitly.

- [x] [Review][Defer] Truncation transparency for long abstracts — **Resolved:** `data_gaps` now includes a per-PMID line when the summary is truncated to **800** characters.

## Dev Notes

### Epic context (Epic 3)

[Source: `_bmad-output/planning-artifacts/epics.md` — Epic 3, Story 3.1]

- **FR6:** Discover and summarize **clinical trial publications** for configured TAs.
- **NFR-I1:** Connectors declare expected behavior; **empty/partial** data → still generate structured output with **transparency** (not silent success).
- **Epic 8** will deepen **TA scope configuration** (FR23); this story should **not** block on Epic 8—use **env-based** TA scope so the pipeline is demonstrable end-to-end.

### Scope boundaries

| In scope | Out of scope |
|----------|----------------|
| Publication/trial **discovery + summary + references** in **`ClinicalOutput`** | Full Epic 8 **configuration UI** |
| **Internal research** ingestion | Story **3.2** |
| **Non-PHI** public/mock sources (PRD MVP) | PHI-heavy enterprise feeds |

### Architecture compliance

[Source: `_bmad-output/planning-artifacts/architecture.md`]

| Topic | Requirement |
|-------|-------------|
| **Agents** | Domain logic in **`agents/`**; return **Pydantic** models; **no direct SQLite** in agents |
| **Integrations** | Outbound HTTP via **`http_client`** / **`integrations/`**; TLS where APIs support (**NFR-S3**) |
| **Contracts** | **snake_case** JSON; version **`schema_version`** on breaking changes |
| **Observability** | Structured logs; **`run_id`** correlation already in pipeline |

### Technical requirements

1. **Reuse** `get_settings()` for all new configuration—**no** ad-hoc `os.environ` reads outside `config.py`.

2. **Downstream compatibility:** **`competitor.run_competitor`** currently ignores `ClinicalOutput` fields; extending **`ClinicalOutput`** is fine. **`Synthesis`** (later epics) will consume richer clinical signal—prefer **stable field names** and document them in the story completion notes.

3. **Rate limits:** NCBI and ClinicalTrials.gov may throttle aggressive clients—implement **conservative** request counts in MVP and surface **rate-limit** classification in logs (**NFR-I2**) when detectable.

4. **Security:** No API keys in repo; optional keys only via **env** if a chosen API requires them (**NFR-S1**).

### Project structure notes

- Primary: **`pharma_rd/agents/clinical.py`**, **`pharma_rd/pipeline/contracts.py`**
- New: **`pharma_rd/integrations/`** modules for PubMed/ClinicalTrials clients if more than ~30 lines each
- Tests: **`tests/agents/test_clinical.py`**, update **`tests/pipeline/test_contracts.py`**

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 3.1]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR6, FR23, NFR-I1, NFR-S3]
- [Source: `_bmad-output/planning-artifacts/architecture.md` — Agents, integrations, FR6–FR13 mapping]
- [Source: `pharma_rd/pipeline/runner.py` — `clinical.run_clinical` invocation]
- [Source: `pharma_rd/http_client.py` — shared HTTP client]
- [Source: `pharma_rd/agents/connector_probe.py` — optional probe]

## Previous story intelligence

[Source: `_bmad-output/implementation-artifacts/2-3-retry-failed-stage-without-re-running-completed-upstream.md`]

- **Resume/retry** paths re-invoke the same **`run_clinical`**; behavior must stay **idempotent** from the perspective of “valid JSON artifact out.”
- **Connector probe** and **`ConnectorFailure`** classification must remain coherent—clinical should not swallow HTTP errors in a way that hides **`integration_error_class`** when the probe or real connector fails.

## Git intelligence

- Recent work: Epic 1–2 delivered **runner**, **scheduler**, **HTTP retries**, **`retry-stage`**. Follow existing **`ruff`**, **`pytest`**, **`uv`** conventions in **`pharma_rd/README.md`**.

## Latest technical notes

- **PubMed E-utilities:** stable HTTP API; NCBI requests a **identifying email/tool** parameter for responsible use—include via settings (optional env) for production-friendly behavior.
- **ClinicalTrials.gov:** public JSON API (v2); good for structured trial metadata; combine with literature sources if PRD “publications” wording requires both—epics allow **summaries** of trial-linked **publications**; document which source satisfies AC in **`README`**.

## Project context reference

- No **`project-context.md`** in repo yet; optional **`bmad-generate-project-context`** for brownfield map after this epic.

## Dev Agent Record

### Agent Model Used

Cursor (GPT-5.1)

### Debug Log References

### Completion Notes List

- Implemented **FR6** via **PubMed E-utilities** (`esearch` → `efetch`) with **`ClinicalOutput` schema_version 2** (`PublicationItem`, `data_gaps`, `integration_notes`).
- **TA scope:** `PHARMA_RD_THERAPEUTIC_AREAS` + `Settings.therapeutic_area_labels()`; empty scope completes with explicit gaps (NFR-I1), no NCBI calls.
- **Logging:** clinical stage emits **`clinical_publications`** (pipeline tests updated); other stages still use **`agent_stub`**.
- **Tests:** `tests/conftest.py` clears **`get_settings` cache** between tests; unit tests mock **`fetch_publications_for_labels`** where needed.
- **Code review (2026-04-05):** PubMed query now requires **`Clinical Trial[Publication Type]`**; **`pubmed_search_pmids`** validates JSON and raises **`ConnectorFailure`** on NCBI **`ERROR`** / non-JSON; truncation recorded in **`data_gaps`**.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/clinical.py`
- `pharma_rd/pharma_rd/integrations/__init__.py`
- `pharma_rd/pharma_rd/integrations/pubmed.py`
- `pharma_rd/tests/conftest.py`
- `pharma_rd/tests/agents/test_clinical.py`
- `pharma_rd/tests/integrations/test_pubmed.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_runner.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`

### Change Log

- 2026-04-05: Story 3.1 implementation — PubMed clinical agent, contract v2, tests, docs.
- 2026-04-05: Code review follow-up — trial publication-type filter, esearch error handling, truncation `data_gaps`; status **done**.

---

**Story completion status:** Done (implementation + code review follow-up).
