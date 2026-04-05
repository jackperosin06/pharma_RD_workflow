# Story 6.2: Ranked opportunities with cross-domain cross-reference

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **R&D scientist**,
I want **a ranked list of formulation or line-extension opportunities with cross-domain rationale**,
so that **I can prioritize judgment time** (FR15).

## Acceptance Criteria

1. **Given** valid upstream structured inputs (Clinical, Competitor, Consumer artifacts for the same `run_id` per FR14)  
   **When** Synthesis completes  
   **Then** structured output contains a **ranked list** of opportunities, each with a **short rationale** that explicitly ties **clinical**, **competitor**, and **consumer** signals (where those domains contributed; if a domain had no usable items, rationale must **state that gap** rather than inventing ties)  
   **And** **ranking criteria** are **versioned** in output metadata for auditability (e.g. a stable string + optional integer bump when logic changes)

## Tasks / Subtasks

- [x] **Contract (FR15)** — Extend `SynthesisOutput` in `pharma_rd/pharma_rd/pipeline/contracts.py`:
  - [x] Bump **`schema_version`** to **3** (additive; preserve FR14 fields: `run_id`, upstream schema version ints, `aggregated_upstream_gaps`).
  - [x] Add **`ranking_criteria_version`** (string, required) — e.g. `"cross_domain_v1"` — documented as the audit handle for ranking logic.
  - [x] Add **`ranked_opportunities`**: ordered list (best rank first). Each item needs at minimum: stable **`rank`** (1-based), human-readable **`title`**, **`rationale_short`** (string) that references clinical + competitor + consumer contribution in one or two sentences, and a **`domain_coverage`** indicator (e.g. which of the three domains supplied signal for this row — use a small nested model or explicit booleans/strings; `extra="forbid"` on all new models).
  - [x] Keep **`extra="forbid"`** everywhere; snake_case JSON.
- [x] **Synthesis logic** — Update `pharma_rd/pharma_rd/agents/synthesis.py` `run_synthesis(...)`:
  - [x] Implement a **deterministic**, **documented** cross-domain merge (no LLM calls required for MVP): e.g. build candidates from upstream lists (`publication_items`, `internal_research_items`, competitor item lists, consumer `feedback_themes` / `pharmacy_sales_trends` / `unmet_need_demand_signals`), score or order by explicit rules so the same inputs always yield the same ranking, and compose **`rationale_short`** from actual upstream titles/summaries (not generic filler).
  - [x] **Empty / sparse upstream:** still emit a **valid** JSON structure: e.g. zero ranked rows **or** a single explicit “insufficient cross-domain signal” row only if product-empty behavior is clearer — **prefer** zero rows plus existing `aggregated_upstream_gaps` documenting why, unless a non-empty list is required for operators; **document the chosen behavior** in Dev Notes below and in tests.
  - [x] Log one structured line when ranking completes (e.g. `event`, `ranked_count`, `ranking_criteria_version`) — extend `logging_setup` JSON allowlist if new `extra` keys are introduced.
- [x] **Runner** — No change to loading path expected if runner already passes three models into `run_synthesis`; verify persisted synthesis JSON still round-trips.
- [x] **Tests** — `tests/agents/test_synthesis.py`: cases for (1) rich upstream → multiple ranked rows with rationale containing tokens from each domain where applicable; (2) empty lists → deterministic outcome per chosen empty behavior; (3) contract round-trip in `tests/pipeline/test_contracts.py` for `SynthesisOutput` v3 defaults.
- [x] **README** — Short note under synthesis / FR15: ranked list + `ranking_criteria_version` (one paragraph).

### Review Findings

- [x] [Review][Decision] **Index alignment vs same opportunity** — **Resolved (product):** MVP accepts **index-aligned** pairing of the *i*-th **usable** row per domain (positional heuristic); documented in README. Follow-up may add entity/keyword matching.

- [x] [Review][Patch] **Silent per-domain cap** — **Resolved:** Truncation recorded as **`[synthesis] … truncated for ranking`** lines appended to **`aggregated_upstream_gaps`** when usable rows exceed five per domain.

- [x] [Review][Patch] **`rationale_short` length** — **Resolved:** Final string clipped to **`_RATIONALE_MAX_LEN` (280)** characters in **`_compose_rationale`**.

- [x] [Review][Patch] **Blank upstream text** — **Resolved:** Collectors skip tuples where title and summary are empty after strip (`_pair_usable`).

- [x] [Review][Defer] **v2 synthesis JSON replay** — Loading older `schema_version` 2 files with the v3 model can populate default `ranking_criteria_version` / `ranked_opportunities`, which can misread historical runs as FR15-ranked; document or add migration if replay matters. [Evidence: `pharma_rd/pharma_rd/pipeline/contracts.py` `SynthesisOutput`]

- [x] [Review][Defer] **README scope** — Same branch adds Epic 5 consumer env/schema bullets alongside Epic 6 synthesis; acceptable for integration branch but not isolated to story 6.2 files only. [Evidence: `pharma_rd/README.md` diff]

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR15** | Cross-reference domains → **ranked** opportunities; **not** full evidence/commercial sections (those are **Story 6.3**, FR16/FR17). |
| **FR14** | Already satisfied by 6.1 — keep three-model snapshot and gap aggregation. |
| NFR | Deterministic ranking for testability; version string for audit. |

### Scope boundary (do not implement in 6.2)

- **Story 6.3** will add per-item **verifiable evidence references** and **commercial viability** sections. For **6.2**, do **not** add large FR16/FR17 structures to each row unless minimal placeholders are required for schema stability — prefer **thin** rows: rank, title, rationale, domain coverage + **`ranking_criteria_version`** at top level.

### Architecture compliance

- **Agents** produce Pydantic only; **persistence** writes artifacts — unchanged boundary [Source: `_bmad-output/planning-artifacts/architecture.md` — Architectural boundaries].
- **Delivery does not re-rank** — all ranking lives in synthesis [Source: same file, table “Architectural boundaries”].
- **snake_case** JSON for artifacts and logs [Source: `architecture.md` — JSON conventions].

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Synthesis | `pharma_rd/pharma_rd/agents/synthesis.py` |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` (if new log `extra` keys) |
| Tests | `pharma_rd/tests/agents/test_synthesis.py`, `pharma_rd/tests/pipeline/test_contracts.py` |
| Docs | `pharma_rd/README.md` |

### Previous story intelligence (6.1)

- **`run_synthesis(run_id, clinical, competitor, consumer)`** — `run_id` mismatch → `ValueError`; keep this guard.
- **`SynthesisOutput` v2** fields and **`aggregated_upstream_gaps`** — preserve; extend additively to v3.
- **`read_stage_artifact_model`** / artifact errors — unchanged; synthesis still receives validated models from runner.
- Upstream schema versions: Clinical **2**, Competitor **4**, Consumer **4** — rationale should draw from typed item fields above, not raw JSON.

### Testing requirements

- Ruff line length (88) on new strings.
- Round-trip `model_validate_json` for `SynthesisOutput` after changes.
- No regression: pipeline run still completes through synthesis stage with fixture or default run.

### Latest tech / deps

- Python **3.12**, **Pydantic v2** — no new runtime dependencies expected.

### Project structure notes

- Code lives under **`pharma_rd/pharma_rd/`** (actual repo layout); architecture diagram may show `src/pharma_rd/` — follow **repository** paths.

### Empty upstream behavior (implemented)

- When **all** upstream item lists are empty, **`ranked_opportunities`** is **`[]`**; gaps remain in **`aggregated_upstream_gaps`** when upstream reported **`data_gaps`** / **`integration_notes`**.

### MVP ranking model (product)

- **Index alignment:** The *i*-th **usable** clinical, competitor, and consumer row are paired for one ranked row; this is **positional**, not proof of a single shared entity (accepted for MVP per code review **1a**).

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`SynthesisOutput` schema v3** — `ranking_criteria_version` **`cross_domain_v1`**, **`ranked_opportunities`** with **`DomainCoverage`** + **`RankedOpportunityItem`**.
- **Deterministic ranking** — index-aligned **usable** slices (blank text skipped), per-domain cap **5** with **`[synthesis]`** truncation lines in **`aggregated_upstream_gaps`**; **`rationale_short`** capped at 280 chars; sorted by domain coverage count then slice index.
- **Logging** — **`synthesis_ranking_complete`** with **`ranked_count`**, **`ranking_criteria_version`**; JSON formatter allowlist extended.
- **Tests** — rich upstream, partial domains, empty lists; pipeline logging asserts new event.

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/6-2-ranked-opportunities-with-cross-domain-cross-reference.md`

### Change Log

- 2026-04-05: Story 6.2 implemented — FR15 ranked opportunities, `cross_domain_v1`, tests, README; sprint → review.
- 2026-04-05: Code review — findings appended; 1 decision-needed, 3 patch, 2 defer, 2 dismissed; sprint → in-progress.
- 2026-04-05: Code review **1a** + batch **0** — truncation notes in gaps, rationale cap, skip blank rows; README; tests; sprint → done.

## References

- Epic 6 / Story 6.2: `_bmad-output/planning-artifacts/epics.md`
- PRD FR15: `_bmad-output/planning-artifacts/prd.md` — Synthesis & ranking
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — FR14–FR17 mapping, boundaries
- Previous: `_bmad-output/implementation-artifacts/6-1-consume-monitoring-agent-outputs-for-a-run.md`

### Questions / clarifications (optional — for product owner)

1. If all three upstream domain lists are empty, should **`ranked_opportunities`** be **[]** only, or must there be at least one explanatory row? Story leans **[]** + gaps; confirm for UX consistency with Epic 7 reporting.

---

**Story completion status:** done — Code review follow-ups applied; tests green.
