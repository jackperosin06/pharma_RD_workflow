# Story 6.3: Evidence references and commercial viability per item

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **R&D scientist**,
I want **each ranked item to include verifiable evidence and commercial viability framing**,
so that **I can validate claims before pursuit** (FR16, FR17).

## Acceptance Criteria

1. **Given** a **ranked item** in synthesis output (FR15 list produced for the run)  
   **When** a human reviews that item  
   **Then** the item includes **references or links suitable for verification** drawn from upstream structured data where available (FR16) — not invented URLs  
   **And** the item includes a **qualitative commercial viability** section (FR17) — explicit text suitable for MVP judgment (not numeric forecasts unless already present upstream)

## Tasks / Subtasks

- [x] **Contract (FR16 / FR17)** — Extend `pharma_rd/pharma_rd/pipeline/contracts.py`:
  - [x] Bump **`SynthesisOutput.schema_version`** to **4** (additive; keep FR14–FR15 fields: `run_id`, upstream schema ints, `aggregated_upstream_gaps`, `ranking_criteria_version`, `ranked_opportunities` structure).
  - [x] Extend **`RankedOpportunityItem`** with:
    - **`evidence_references`**: list of small nested models (preferred) or structured strings with **`extra="forbid"`** — each entry should identify **domain** (`clinical` | `competitor` | `consumer`), a **short label** (e.g. upstream title/theme), and a **reference** string suitable for verification (PMID, URL, file path, or source label from upstream JSON — mirror `PublicationItem.reference`, `RegulatoryApprovalItem.reference`, `ConsumerFeedbackThemeItem.source`, etc.).
    - **`commercial_viability`**: string — qualitative MVP framing (e.g. demand signal vs competition pressure vs clinical relevance); must be **non-empty** when the ranked row exists, or document explicit empty-string behavior if product prefers “insufficient data” wording inside the string.
  - [x] Keep **`extra="forbid"`** on all new models; **snake_case** JSON.

- [x] **Synthesis population** — Update `pharma_rd/pharma_rd/agents/synthesis.py`:
  - [x] When building each **`RankedOpportunityItem`**, populate **`evidence_references`** from the **same index-aligned tuples** (`ci`, `pi`, `ui`) already used for title/rationale: map **reference/source** fields from the underlying upstream item types (see contracts: `PublicationItem` / `InternalResearchItem` **`reference`**, competitor items’ **`reference`**, consumer **`source`** / **`scope`** where appropriate).
  - [x] For a domain **missing** at that slice index, **omit** evidence entries for that domain (or include zero rows for that domain — do not fabricate links).
  - [x] **`commercial_viability`**: implement a **deterministic**, **documented** template (no LLM) combining signals from the three tuples when present — e.g. one or two sentences on addressable demand, competitive/regulatory context, and clinical relevance; if only one domain has data, state what is unknown for the others without inventing facts.
  - [x] **Logging** — optional structured line or extend existing ranking log with counts of evidence refs per run (only if new `extra` keys are added — extend `logging_setup` allowlist).

- [x] **Tests** — `tests/agents/test_synthesis.py`: (1) rich upstream → at least one ranked row with **non-empty** `evidence_references` containing expected substrings from upstream **reference/source** fields; (2) `commercial_viability` present and contains deterministic tokens; (3) contract round-trip in `tests/pipeline/test_contracts.py` for **`SynthesisOutput` v4** / default `RankedOpportunityItem` shapes.

- [x] **README** — One short paragraph under **Synthesis**: FR16/FR17 fields on each ranked row; point to **`schema_version` 4**.

### Review Findings

- [x] [Review][Patch] **`_verification_ref` fallback `"unverified"`** — **Resolved:** **`_verification_ref`** now takes **`fallback=`** (title/theme/summary-derived); **`summary`** included in candidate parts; no **`"unverified"`** sentinel.

- [x] [Review][Patch] **Evidence `reference` clipped to 200 chars** — **Resolved:** **`_REFERENCE_MAX_LEN = 500`** for **`reference`** only; README documents cap and fallback behavior.

- [x] [Review][Defer] **Legacy `SynthesisOutput` v3 artifacts** — On-disk v3 JSON lacks FR16/FR17 fields; consumers must re-run or migrate — README notes this; optional migration helper is a future story.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR16** | Verifiable **references** per ranked item — tie to upstream **`reference`** / **`source`** fields. |
| **FR17** | **Qualitative** commercial viability text per item — MVP: rule-based synthesis from available signals. |
| **FR15** | Preserved — ranking, `ranking_criteria_version`, `rationale_short`, `domain_coverage` remain. |
| **Story 6.4** | **Do not** implement FR27/FR28 (quiet-run / scan summary) here — separate story. |

### Architecture compliance

- **Agents** return Pydantic only; **Delivery** does not add evidence — synthesis owns FR16/FR17 payload [Source: `_bmad-output/planning-artifacts/architecture.md` — Architectural boundaries].
- **snake_case** JSON for artifacts and logs.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Synthesis | `pharma_rd/pharma_rd/agents/synthesis.py` |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` (if new log `extra` keys) |
| Tests | `pharma_rd/tests/agents/test_synthesis.py`, `tests/pipeline/test_contracts.py` |
| Docs | `pharma_rd/README.md` |

### Previous story intelligence (6.2)

- **`RankedOpportunityItem`** currently: **`rank`**, **`title`**, **`rationale_short`**, **`domain_coverage`** — extend **additively**; bump **`SynthesisOutput.schema_version`** **3 → 4**.
- **Index-aligned usable slices**, **`_pair_usable`**, **`_RATIONALE_MAX_LEN`**, **`[synthesis]` truncation** lines — preserve behavior; new fields attach per row.
- **`run_synthesis(run_id, clinical, competitor, consumer)`** signature unchanged.

### Technical requirements (guardrails)

- **No fabricated PMIDs/URLs** — only propagate or concatenate what upstream models already contain.
- **Deterministic** commercial viability strings for tests (same inputs → same output).
- **Ruff** line length 88 on new strings.

### Project structure notes

- Package root: **`pharma_rd/pharma_rd/`** (repository layout).

### Latest tech / deps

- Python **3.12**, **Pydantic v2** — no new runtime dependencies expected unless you introduce a shared helper module (prefer keeping logic in `synthesis.py` for MVP).

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`EvidenceReferenceItem`** — `domain` / `label` / `reference`; **`RankedOpportunityItem`** + **`evidence_references`**, **`commercial_viability`**; **`SynthesisOutput` v4**.
- **Collectors** return `(title, summary, EvidenceReferenceItem)` rows per domain; **`_verification_ref`** prefers upstream reference/source fields.
- **`_compose_commercial_viability`** — deterministic FR17 text per coverage pattern.
- **Logging:** **`evidence_ref_count`** on **`synthesis_ranking_complete`**.

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/6-3-evidence-references-and-commercial-viability-per-item.md`

### Change Log

- 2026-04-06: Story 6.3 implemented — FR16/FR17, schema v4, tests, README; sprint → review.
- 2026-04-06: Code review — 2 patch, 1 defer, 1 dismissed; sprint → in-progress.
- 2026-04-06: Code review batch **0** — fallback refs + 500-char cap + README; patches cleared; sprint → done.

## References

- Epic 6 / Story 6.3: `_bmad-output/planning-artifacts/epics.md`
- PRD FR16–FR17: `_bmad-output/planning-artifacts/prd.md` — Synthesis & ranking section
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — FR14–FR17 mapping
- Prior implementation: `_bmad-output/implementation-artifacts/6-2-ranked-opportunities-with-cross-domain-cross-reference.md`
- Upstream field names: `pharma_rd/pharma_rd/pipeline/contracts.py` — `PublicationItem`, `InternalResearchItem`, competitor item types, consumer theme/sales/unmet types

### Git intelligence (recent commits)

- Repo history on `main` is pre–Epic 6 merge; follow **6.2** file patterns and tests in the working tree for conventions.

### Web / version note

- No new third-party APIs required; evidence strings are **passthrough** from existing stage outputs.

### Questions (optional — product)

1. Should **`evidence_references`** be strictly **HTTP(S) URLs**, or are **PMID:** / **file:** / free-text labels acceptable if that is all upstream provides? (Story assumes **verification-suitable strings** mirroring upstream — not only URLs.)

---

## Appendix: PRD excerpts (FR16–FR17)

From planning artifacts — **FR16:** supporting **evidence references** suitable for **human verification**; **FR17:** **commercial viability** assessment (**qualitative** in MVP unless otherwise specified).

---

**Story completion status:** done — Code review patches applied; tests green.
