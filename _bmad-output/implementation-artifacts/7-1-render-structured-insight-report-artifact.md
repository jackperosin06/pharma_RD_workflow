# Story 7.1: Render structured insight report artifact

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **a rendered structured insight report for each completed run**,
so that **recipients receive a consistent deliverable** (FR18).

## Acceptance Criteria

1. **Given** persisted **`SynthesisOutput`** for **`run_id`** (same shape as synthesis stage artifact)  
   **When** the Delivery stage runs  
   **Then** a **human-readable report file** is written under the artifact root (implementation choice: **Markdown** recommended for MVP—opens in any editor/browser; avoid new heavy dependencies unless justified).

2. **Given** that report  
   **When** an operator inspects paths and DB metadata  
   **Then** the delivery stage still persists **`output.json`** validated by **`DeliveryOutput`** (bump **`schema_version`** as needed) and **`stage_artifacts`** records the stage (existing persistence pattern).

3. **Given** the report content  
   **When** reviewed against the agreed structure  
   **Then** it includes **sections** for: **run / summary** (incl. FR27 **`signal_characterization`** and FR28 **`scan_summary_lines`** when present on synthesis), **ranked opportunities** (title, rationale, evidence references, commercial viability per row—mirroring synthesis, no re-ranking), and a **governance / disclaimer** block (**placeholder** wording is acceptable in 7.1; **Story 7.4** hardens FR22 language).

## Tasks / Subtasks

- [x] **Contract** — Extend `pharma_rd/pharma_rd/pipeline/contracts.py`:
  - [x] Bump **`DeliveryOutput.schema_version`** to **2** (additive); keep **`extra="forbid"`**.
  - [x] Add fields so operators/logs can locate the report, e.g. **`report_relative_path`** (`str`, POSIX-style path under artifact root) and **`report_format`** (literal **`markdown`** for MVP) — adjust names if you prefer but document in README.
  - [x] Do **not** duplicate full synthesis payload inside **`DeliveryOutput`**; the report file is the human view.

- [x] **Rendering** — Implement in `pharma_rd/pharma_rd/agents/delivery.py` (or `pharma_rd/pharma_rd/agents/delivery/` package if you split helpers—keep imports stable for runner):
  - [x] **Signature** — Add **`artifact_root: Path`** (or equivalent) so the report can be written under the configured root. Update **`runner.py`** call site: `delivery.run_delivery(run_id, synthesis, artifact_root)` (order as you prefer; document in README).
  - [x] **`run_delivery`** loads nothing extra from disk beyond **`synthesis`** (already passed in) — **do not re-rank** or mutate ranked rows [Source: architecture — Delivery boundary].
  - [x] Write **UTF-8** Markdown to **`{artifact_root}/{run_id}/delivery/report.md`** (or the path encoded in **`report_relative_path`**) using atomic write (tmp + replace) consistent with `write_stage_artifact` safety; **either** call a shared helper from `persistence/artifacts.py` for the second file **or** implement safe write locally with a one-line comment pointing to the same pattern.
  - [x] Escape or format bullet text so markdown special characters in upstream strings do not break structure (minimal: prefer fenced blocks or consistent indentation for free text).
  - [x] Include **governance** section with clear **placeholder** that items are **recommendations** (7.4 will refine FR22 copy).

- [x] **Runner / persistence** — `pharma_rd/pharma_rd/pipeline/runner.py`:
  - [x] After building **`DeliveryOutput`**, ensure **`write_stage_artifact`** still runs for **`output.json`**; report file must exist **before** or **as part of** stage completion (order documented in dev notes if tricky).

- [x] **Logging** — If new structured log **`extra`** keys are introduced, extend `pharma_rd/pharma_rd/logging_setup.py` allowlist (e.g. **`report_relative_path`**, **`report_byte_size`**).

- [x] **Tests** — Add `pharma_rd/tests/agents/test_delivery.py`:
  - [x] **tmp_path** artifact root: run **`run_delivery`** with a **rich** `SynthesisOutput` fixture → assert **`report.md`** exists, contains **`run_id`**, at least one ranked row substring, and disclaimer section marker.
  - [x] **`DeliveryOutput`** round-trip / defaults in `tests/pipeline/test_contracts.py` for **v2**.

- [x] **README** — Under Delivery / pipeline: artifact layout **`{run_id}/delivery/report.md`**, **`DeliveryOutput`** v2 fields, pointer that **7.2** handles distribution.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR18** | Rendered structured insight report for completed run. |
| **FR27–FR28** | Already on **`SynthesisOutput`** — surface in report summary (not recomputed). |
| **FR22** | Full compliance copy is **7.4**; 7.1 needs visible **governance** section + placeholder. |

### Architecture compliance

- **Delivery** consumes synthesis only; **does not** re-rank or alter evidence [Source: `_bmad-output/planning-artifacts/architecture.md` — Architectural boundaries].
- **Artifacts:** filesystem + SQLite metadata [Source: architecture — Artifact storage].
- **snake_case** JSON for **`output.json`**.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Delivery | `pharma_rd/pharma_rd/agents/delivery.py` (and optional `pharma_rd/pharma_rd/agents/delivery/*.py`) |
| Persistence | `pharma_rd/pharma_rd/persistence/artifacts.py` (optional shared binary write helper) |
| Runner | `pharma_rd/pharma_rd/pipeline/runner.py` |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` |
| Tests | `pharma_rd/tests/agents/test_delivery.py`, `pharma_rd/tests/pipeline/test_contracts.py` |
| Docs | `pharma_rd/README.md` |

### Previous story intelligence (6.4)

- **`SynthesisOutput`** **v5**: **`signal_characterization`**, **`scan_summary_lines`** — report summary should echo these for transparency.
- **`RankedOpportunityItem`**: **`evidence_references`**, **`commercial_viability`** — render per row; do not invent URLs.

### Technical requirements (guardrails)

- **Deterministic** rendering for tests (stable ordering: follow **`rank`** on opportunities).
- **No new dependencies** unless required for Markdown safety (prefer stdlib).
- **Ruff** line length **88** for new code.

### Project structure notes

- Import package: **`pharma_rd/pharma_rd/`**; runner already imports **`pharma_rd.agents.delivery`**.

### Git intelligence

- Follow patterns from **`agents/synthesis.py`** (logging, connector probe) and **`persistence/artifacts.py`** (atomic JSON write).

### Latest tech / deps

- Python **3.12**, **Pydantic v2**.

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`DeliveryOutput` v2:** `report_relative_path`, `report_format` **`markdown`**, `report_byte_size`.
- **`write_utf8_artifact_atomic`** in `artifacts.py` — tmp+replace for **`report.md`**.
- **`run_delivery(run_id, synthesis, artifact_root)`** — **`delivery_report_written`** log; runner updated.
- **Tests:** `test_delivery.py`, legacy v1 JSON in **`test_contracts`**; **`test_logging`** expects **`delivery_report_written`** (replaces delivery **`agent_stub`**).

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/persistence/artifacts.py`
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_delivery.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/7-1-render-structured-insight-report-artifact.md`

### Change Log

- 2026-04-06: Story 7.1 implemented — FR18 Markdown report, `DeliveryOutput` v2, tests, README; sprint → review.
- 2026-04-06: Code review — clean (no patch/defer items); sprint → done.

## References

- Epic 7 / Story 7.1: `_bmad-output/planning-artifacts/epics.md`
- PRD FR18: `_bmad-output/planning-artifacts/prd.md`
- Architecture — Delivery: `_bmad-output/planning-artifacts/architecture.md`
- Contracts: `pharma_rd/pharma_rd/pipeline/contracts.py` — `SynthesisOutput`, `DeliveryOutput`
- Prior epic: `_bmad-output/implementation-artifacts/6-4-quiet-run-and-scan-summary-transparency-in-synthesis-output.md`

### Questions (optional — product)

1. **PDF/HTML** in 7.1 vs Markdown-only MVP — story assumes **Markdown** unless product insists otherwise (faster, no extra deps).

---

**Story completion status:** done — Code review passed; acceptance criteria satisfied.
