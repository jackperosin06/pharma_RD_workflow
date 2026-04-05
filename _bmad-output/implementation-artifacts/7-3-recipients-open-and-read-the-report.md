# Story 7.3: Recipients open and read the report

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **R&D scientist** or **marketing lead**,
I want **to open and read the structured report on standard hardware**,
so that **I can consume insights without special software** (FR20, FR21, NFR-P2).

## Acceptance Criteria

1. **Given** a **delivered** insight report (same logical artifact **R&D** and **marketing** receive per FR19 / story 7.2 — e.g. `report.md` at the file-drop paths or attached as a file)  
   **When** a recipient opens it on a **typical corporate laptop** (plain-text editor, browser, or standard email client — **no proprietary pharma_RD client**)  
   **Then** the **run summary**, **ranked opportunities**, and **evidence** (and **commercial viability** where rendered) are **discernible** without specialized tooling.

2. **Given** the report file(s) produced for a run  
   **When** automated checks run (CI)  
   **Then** there is **deterministic** coverage that the **readable artifact** is **UTF-8**, contains expected **structural markers** (e.g. summary / ranked / governance sections consistent with `delivery.py` rendering), and — if **file_drop** is used — the **distributed copy** matches the **canonical** `{artifact_root}/{run_id}/delivery/report.md` (byte-for-byte or documented normalization).

3. **Given** NFR-P2 (**browser or standard email/PDF — implementation open**)  
   **When** documenting the recipient path  
   **Then** **README** includes a short **“For recipients”** subsection: at least one **zero-install** path (e.g. open `report.md` in a default editor **or** open a **generated static HTML** view in a normal browser — pick one primary path and test/document it; do not require a custom desktop app).

## Tasks / Subtasks

- [x] **Readability contract (tests)** — Add a small **shared helper** (e.g. under `pharma_rd/pharma_rd/` or `tests/` only — prefer **importable** if delivery tests reuse it) that, given a **`Path` to `report.md`**, asserts:
  - [x] Decodes as **UTF-8** without replacement.
  - [x] Contains markers for **run summary**, **ranked opportunities**, and **governance/disclaimer** section (align with current `_render_markdown` headings — avoid brittle full-string match; prefer stable `##` / `###` patterns).
  - [x] For a **rich** `SynthesisOutput` fixture, at least one ranked row’s **title** or **rationale** substring appears (proves opportunities are not dropped).

- [x] **Distribution path parity** — Extend or add tests (e.g. `tests/integrations/test_distribution.py` or `tests/agents/test_delivery.py`):
  - [x] **Given** `distribution_channel=file_drop` and tmp dirs, after a **full** delivery invocation (or distribution-only with existing `report.md`), assert **R&D** and **marketing** copies exist and **pass the same readability helper** as the canonical artifact.

- [x] **Recipient documentation** — `pharma_rd/README.md`:
  - [x] New **“For recipients (FR20 / FR21 / NFR-P2)”** (or similar) bullets: where files land (`rd/`, `marketing/` under drop dir), that **both roles** get the **same** content, and **how** to open (editor vs browser).
  - [x] If you add **optional `report.html`** (see below), document **double-click / file://** in Chrome/Edge/Safari.

- [x] **Optional — static HTML for browser-first NFR-P2:** If plain Markdown is insufficient for “opens in browser without extensions,” add **`report.html`** next to **`report.md`** under `{run_id}/delivery/` (stdlib-only: escape text, semantic headings, minimal CSS). Wire **`DeliveryOutput`** only if new fields are needed (prefer **additive** bump e.g. v4 **or** document HTML as companion file without contract change — **do not** break v3 consumers). **Copy `report.html` in file_drop** alongside `report.md` if implemented.

- [x] **Out of scope / sequencing:** **FR22** disclaimer **wording** and visibility polish is **Story 7.4** — do not block 7.3 on copy changes beyond ensuring the **governance** section remains **present** and readable.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR20 / FR21** | Both personas **read the same** structured report for a run; 7.2 already delivers to both roles. |
| **NFR-P2** | No proprietary client; **browser, email, or PDF** — document the chosen practice-build path clearly. |
| **Epic 7** | 7.1 renders; 7.2 distributes; **7.3** proves **consumption** quality and documents recipient workflow. |

### Architecture compliance

- **Delivery boundary:** Do **not** re-rank or alter synthesis — 7.3 **validates** and optionally **adds a parallel HTML view** of existing rendered content [Source: `_bmad-output/planning-artifacts/architecture.md` — Delivery consumes synthesis only].
- **Integrations / I/O:** Distribution stays in **`integrations/report_distribution.py`**; extend **copy** list if **`report.html`** is added [Source: architecture — outbound I/O centralized].
- **Artifacts:** Filesystem under **`PHARMA_RD_ARTIFACTS_ROOT`**; keep **atomic write** patterns from **`write_utf8_artifact_atomic`** for any new file.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Delivery / render | `pharma_rd/pharma_rd/agents/delivery.py` (only if adding HTML or shared validation used here) |
| Distribution | `pharma_rd/pharma_rd/integrations/report_distribution.py` (if copying extra files) |
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` (only if **`DeliveryOutput`** must reference `report.html`) |
| Tests | `pharma_rd/tests/agents/test_delivery.py`, `pharma_rd/tests/integrations/test_distribution.py` (new helper imports) |
| Docs | `pharma_rd/README.md` |

### Previous story intelligence (7.2)

- Canonical report: **`{artifact_root}/{run_id}/delivery/report.md`**; **`DeliveryOutput` v3** has **`distribution_*`** fields.
- File drop copies: **`{drop_dir}/rd/{run_id}/report.md`**, **`{drop_dir}/marketing/{run_id}/report.md`**, **`manifest.json`** — **reuse** these paths in tests.
- **SMTP** not implemented; do not require network tests for 7.3.

### Technical requirements (guardrails)

- **Python 3.12**; **Ruff** 88; **Pydantic v2** for any contract edits.
- **No new heavy dependencies** for MVP (stdlib-first for HTML if added).
- **Deterministic** tests (**tmp_path**, no real SMTP).

### Project structure notes

- Package root **`pharma_rd/pharma_rd/`**; tests mirror existing **`tests/agents/`**, **`tests/integrations/`**.

### Git intelligence

- Recent commits are **monolithic epics** on `main`; follow **existing** patterns in **`test_delivery.py`** / **`test_distribution.py`** for fixtures and caplog.

### Latest tech / deps

- Stay on **locked** `uv` dependencies; no upgrade spikes required for this story.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

—

### Completion Notes List

- **Code review (2026-04-05):** Applied patch — `distribute_insight_report` docstring now mentions **`report.html`** when present.
- Added **`pharma_rd.readability.validate_readable_insight_report`** (UTF-8 + section markers + optional snippets).
- Delivery writes **`report.html`** (stdlib **`html.escape`**) alongside **`report.md`**; **`DeliveryOutput`** extended with **`report_html_relative_path`** / **`report_html_byte_size`** (additive v3).
- File-drop copies **`report.html`** to R&D and marketing; **`manifest.json`** gains optional HTML paths when present.
- README **For recipients** subsection; tests cover parity, readability, contracts legacy v3, logging extras.

### File List

- `pharma_rd/pharma_rd/readability/__init__.py`
- `pharma_rd/pharma_rd/readability/insight_report.py`
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/pharma_rd/integrations/report_distribution.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/README.md`
- `pharma_rd/tests/agents/test_delivery.py`
- `pharma_rd/tests/integrations/test_distribution.py`
- `pharma_rd/tests/readability/test_insight_report.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_logging.py`

### Change Log

- 2026-04-05: Story 7.3 — readability validation, static HTML report, distribution + docs + tests.

### Review Findings

- [x] [Review][Patch] Update `distribute_insight_report` module docstring — it still describes copying only `report.md`; file-drop now also copies `report.html` when present — [`pharma_rd/pharma_rd/integrations/report_distribution.py` line 36] — fixed 2026-04-05
- [x] [Review][Defer] Markdown vs HTML render paths duplicate structure — [`pharma_rd/pharma_rd/agents/delivery.py`] vs [`pharma_rd/pharma_rd/readability/insight_report.py`] — headings must stay aligned manually; optional future refactor to a single template or shared section list — deferred, pre-existing tradeoff for MVP

## References

- Epic 7 / Story 7.3: `_bmad-output/planning-artifacts/epics.md`
- PRD FR20, FR21, NFR-P2: `_bmad-output/planning-artifacts/prd.md`
- Architecture — MVP UI / artifacts: `_bmad-output/planning-artifacts/architecture.md`
- Prior: `_bmad-output/implementation-artifacts/7-2-distribute-report-to-r-d-and-marketing-recipients.md`, `7-1-render-structured-insight-report-artifact.md`

---

**Story completion status:** done — Code review patch applied (docstring); **`uv run ruff check`** and **`uv run pytest`** passing.
