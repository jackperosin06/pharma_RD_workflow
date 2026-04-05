# Story 6.4: Quiet-run and scan-summary transparency in synthesis output

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **marketing lead**,
I want **the synthesis output to distinguish low-signal runs and summarize what was scanned**,
so that **I trust the report when little changed** (FR27, FR28).

## Acceptance Criteria

1. **Given** any completed Synthesis run  
   **When** the structured `SynthesisOutput` is produced  
   **Then** it includes an explicit **net-new vs quiet** characterization aligned with FR27 (not prose-only — a structured field consumers can rely on).

2. **Given** the same run  
   **When** output is inspected  
   **Then** it includes a **high-level summary of what was scanned** (sources/scopes) drawn from upstream structured data — FR28 — without inventing connectors the pipeline did not touch.

## Tasks / Subtasks

- [x] **Contract (FR27 / FR28)** — Extend `pharma_rd/pharma_rd/pipeline/contracts.py`:
  - [x] Bump **`SynthesisOutput.schema_version`** to **5** (additive; preserve FR14–FR17: `run_id`, upstream schema ints, `aggregated_upstream_gaps`, `ranking_criteria_version`, `ranked_opportunities`, all `RankedOpportunityItem` fields).
  - [x] Add **FR27** field(s), e.g. a `Literal` (recommended: include **`unknown`** for legacy deserialization) such as **`signal_characterization`**: `quiet` | `net_new` | `mixed` | `unknown` — **document** the deterministic rules in `synthesis.py` (no LLM).
  - [x] Add **FR28** field(s), e.g. **`scan_summary_lines`**: `list[str]` (non-empty for normal runs; empty allowed only when truly no scope data exists) **or** a small nested model with **`extra="forbid"`** — each line should be human-readable and traceable to upstream counts/labels (clinical TAs, competitor item categories, consumer channels/scopes).
  - [x] Keep **`extra="forbid"`** on all models; **snake_case** JSON keys.

- [x] **Synthesis logic** — Update `pharma_rd/pharma_rd/agents/synthesis.py`:
  - [x] Implement **`_characterize_signal(...)`** (name flexible): deterministic classification from **upstream counts**, **ranked row count**, and **domain coverage** patterns already used in ranking — avoid arbitrary magic numbers without a one-line comment and a test.
  - [x] Implement **`_build_scan_summary(...)`**: assemble **high-level** bullets from:
    - **Clinical:** `therapeutic_areas_configured`, `len(publication_items)`, `len(internal_research_items)` (and optionally distinct `source` / `source_label` values where useful).
    - **Competitor:** counts of approvals, disclosures, pipeline disclosures, patent flags; where present, summarize **scopes** (e.g. `matched_scope`, `matched_competitor`) without dumping full row text.
    - **Consumer:** counts of feedback themes, pharmacy sales trends (include **`scope`** strings), unmet-need/demand signals; include **`practice_mode`** when relevant to interpretation.
  - [x] **Do not** fabricate URLs, PMIDs, or connector names not reflected in upstream models or `integration_notes`.
  - [x] **Logging** — extend `logging_setup.py` allowlist if new structured **`extra`** keys are added (e.g. `signal_characterization`, `scan_summary_line_count`).

- [x] **Tests** — `pharma_rd/tests/agents/test_synthesis.py`:
  - [x] Fixture or constructed inputs for a **“quiet”** run → expect **`signal_characterization == "quiet"`** (or your documented equivalent).
  - [x] Fixture for a **material / net-new** pattern → **`net_new`** or **`mixed`** per rules.
  - [x] Assert **`scan_summary_lines`** contains expected **substrings** from upstream (TA names, counts, scopes).
  - [x] `tests/pipeline/test_contracts.py`: round-trip JSON for **`SynthesisOutput` v5**; ensure **v4 JSON** (if you support load) behaves per documented defaults — or document **re-run** only (match README stance from 6.3).

- [x] **README** — Short subsection under **Synthesis**: FR27/FR28 fields, **`schema_version` 5**, and how **Delivery / Epic 7** will consume these fields later (stub delivery unchanged unless story scope explicitly includes it).

### Review checklist (self)

- [x] No new runtime dependencies unless justified.
- [x] Ruff line length **88** on new strings.
- [x] `run_synthesis` signature unchanged.

### Review Findings

- [x] [Review][Patch] **`run_synthesis` docstring** omitted FR27/FR28 — **Resolved:** docstring now mentions FR27–FR28 signal + scan summary (`pharma_rd/pharma_rd/agents/synthesis.py`).

- [x] [Review][Defer] **Scan summary line length** — `_clip(..., 88)` may truncate very long TA or scope lists; deferred (see `deferred-work.md`).

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR27** | Structured distinction: **little net-new signal** vs **material change** — must be **machine-readable** on `SynthesisOutput`. |
| **FR28** | **What was scanned** — high-level, per PRD; tie to **upstream** counts and configured scopes. |
| **NFR-I1** | Partial upstream data still yields a report; transparency fields should reflect **gaps** honestly (can overlap with `aggregated_upstream_gaps`). |
| **Architecture** | FR27–FR28 live in **synthesis metadata** + logging [Source: `_bmad-output/planning-artifacts/architecture.md` — Requirements to structure mapping]. |

### Architecture compliance

- **Agents** return Pydantic only; **Delivery** does not compute FR27/FR28 — synthesis owns these fields [Source: `_bmad-output/planning-artifacts/architecture.md` — Architectural boundaries].
- **snake_case** JSON; stdout logs remain JSON lines with allowlisted extras.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Synthesis | `pharma_rd/pharma_rd/agents/synthesis.py` |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` |
| Tests | `pharma_rd/tests/agents/test_synthesis.py`, `pharma_rd/tests/pipeline/test_contracts.py` |
| Docs | `pharma_rd/README.md` |
| Runner | `pharma_rd/pharma_rd/pipeline/runner.py` — only if resume/load paths need explicit version handling (prefer Pydantic defaults). |

### Previous story intelligence (6.3)

- **`SynthesisOutput`** is **v4** with **`ranked_opportunities`**, **`evidence_references`**, **`commercial_viability`** — extend **additively**; bump **4 → 5**.
- **`_collect_*`**, **`_build_ranked_from_lists`**, **`run_synthesis`** aggregation pattern — reuse upstream objects already loaded for **scan summary**; avoid second disk read.
- **Determinism** — same inputs → same characterization and summary lines (tests lock this).
- **6.3 deferral:** legacy v3 artifacts — same policy for v4 after v5 ship: document **re-run** or optional migration; do not silently mis-label old runs as **`net_new`**.

### Technical requirements (guardrails)

- **Heuristic transparency:** The epic does not prescribe exact thresholds — choose **documented** rules (e.g. based on `len(ranked_opportunities)`, total usable upstream rows, and `DomainCoverage` patterns) and encode them in tests.
- **“Unknown” / legacy:** If old synthesis JSON is loaded without new keys, prefer **safe defaults** (`unknown`, empty summary) over misleading **`quiet`/`net_new`**.
- **`aggregated_upstream_gaps`** remains the detailed gap list; FR28 summary is **operator-facing**, not a duplicate of every gap line.

### Project structure notes

- Package root: **`pharma_rd/pharma_rd/`**; follow existing **`tests/fixtures/`** patterns if new golden JSON is needed.

### Git intelligence (recent commits)

- Repo `main` history may predate Epic 6 merges; treat **6.3 story file** and current **`synthesis.py`** / **`contracts.py`** in the working tree as the **source of truth** for conventions.

### Latest tech / deps

- Python **3.12**, **Pydantic v2** — use `Literal`, `Field`, `model_validate_json` consistent with existing contracts.

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`SynthesisOutput` v5:** `signal_characterization` (`quiet` \| `net_new` \| `mixed`; `unknown` for legacy JSON), `scan_summary_lines` (three clipped lines: clinical / competitor / consumer).
- **`_characterize_signal`:** no ranked rows → `quiet`; any row with ≥2 domains → `net_new`; else `mixed`.
- **`_build_scan_summary`:** counts and scopes from upstream models only; **`synthesis_ranking_complete`** logs `signal_characterization` and `scan_summary_line_count`.
- **Tests:** quiet / net_new / mixed / FR28 TA+scope; v4 JSON defaults; pipeline log asserts allowed characterization values.

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/6-4-quiet-run-and-scan-summary-transparency-in-synthesis-output.md`

### Change Log

- 2026-04-05: Story 6.4 implemented — FR27/FR28, `SynthesisOutput` schema v5, tests, README; sprint → review.
- 2026-04-05: Code review — docstring patch, defer note on 88-char scan lines; sprint → done.

## References

- Epic 6 / Story 6.4: `_bmad-output/planning-artifacts/epics.md`
- PRD FR27–FR28: `_bmad-output/planning-artifacts/prd.md` — Transparency & quiet run behavior
- Architecture FR27–FR28: `_bmad-output/planning-artifacts/architecture.md`
- Prior implementation: `_bmad-output/implementation-artifacts/6-3-evidence-references-and-commercial-viability-per-item.md`
- Upstream shapes: `pharma_rd/pharma_rd/pipeline/contracts.py` — `ClinicalOutput`, `CompetitorOutput`, `ConsumerOutput`

### Questions (optional — product)

1. Should **`quiet`** require **zero** ranked rows, or can a run with **few** rows still be **quiet** if signals are repetitive? (Story leaves heuristic to engineering with **tests** as contract.)

---

**Story completion status:** done — Code review complete; acceptance criteria satisfied.
