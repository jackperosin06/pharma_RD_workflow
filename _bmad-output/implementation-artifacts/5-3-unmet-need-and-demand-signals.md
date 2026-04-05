# Story 5.3: Unmet need and demand signals

Status: done

<!-- Optional: run validate-create-story before dev-story. -->

## Story

As a **workflow operator**,
I want **unmet need / demand signals from market sources**,
so that **synthesis can rank opportunities with demand context** (FR13).

## Acceptance Criteria

1. **Given** configured market sources (may be mock/fixture)  
   **When** the Consumer stage runs  
   **Then** structured output includes **demand / unmet-need** signals **or** explicit **insufficient signal** wording (via `data_gaps` / `integration_notes` as appropriate)  
   **And** outputs remain **non-PHI** by default (NFR-S4)

## Tasks / Subtasks

- [x] **Contract** — Extend `ConsumerOutput`: bump `schema_version` to **4**; add typed model(s) for unmet-need / demand line items (e.g. short **label** or **signal**, **summary**, verifiable **source** reference — align naming with existing `ConsumerFeedbackThemeItem` / `PharmacySalesTrendItem` patterns). Keep `extra="forbid"`. Update `tests/pipeline/test_contracts.py` round-trip.
- [x] **Configuration** — Add `PHARMA_RD_*` settings for optional market/demand feed (fixture path and byte cap — follow **fixture-first** MVP pattern used by `consumer_feedback` / `pharmacy_sales`). Empty string → `None` validators. Document in `.env.example`; no secrets in repo (NFR-S1).
- [x] **Integration** — Add `pharma_rd/integrations/` module for demand/unmet-need JSON (bounded reads, NFR-I1 transparency on parse/IO/empty), mirroring `consumer_feedback.py` / `pharmacy_sales.py` (including clear messages when root key missing/null/not array).
- [x] **Agent** — Extend `run_consumer`: merge demand signals into output; when path **not** configured, explicit note in `integration_notes` or `data_gaps` (NFR-I1) stating FR13 / insufficient configuration; when configured but empty/unreadable, transparent explanation; when data present, populate the new list with **sources** filled.
- [x] **Logging** — Structured JSON log event for demand/unmet-need outcome (count and/or skipped) consistent with `consumer_feedback` / `consumer_pharmacy_sales`; extend `logging_setup` field allowlist if needed.
- [x] **Tests** — Extend `tests/agents/test_consumer.py`: not configured, empty fixture, happy path with sources; contract tests for v4; logging tests if new `event` added.
- [x] **Docs** — `README.md` and `.env.example` for FR13 env vars and schema v4.

### Review Findings

- [x] [Review][Patch] `run_consumer` docstring omitted FR13 — [`pharma_rd/pharma_rd/agents/consumer.py:37`] — **Resolved:** docstring now mentions FR13 unmet-need/demand.

- [x] [Review][Defer] **`_resolve_config_path` duplication** — [`pharma_rd/pharma_rd/integrations/unmet_need_demand.py:12`] — same helper as `consumer_feedback` / `pharmacy_sales`; consolidate in a shared module when touching integrations.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| FR13 | Unmet need / demand signals from configured **market** sources |
| NFR-I1 | Missing/empty/bad feeds → stage still completes + **transparent** gaps or notes |
| NFR-S4 | Non-PHI MVP — no patient identifiers in fixtures or summaries |
| Prior | `ConsumerOutput` v3 (5.2) — extend **additively**; **do not** implement Synthesis consumption (Epic 6) |

### Architecture compliance

- **Settings:** `get_settings()` only; `PHARMA_RD_` prefix; optional paths use same empty-string→`None` pattern as `consumer_feedback_path` / `pharmacy_sales_path`.
- **Handoff:** Consumer stage only; persist versioned JSON for downstream Epic 6 — no changes to `SynthesisOutput` in this story.
- **Integrations:** HTTP (if ever added later) stays under `integrations/` with timeouts/classification per architecture — **MVP is fixture JSON** unless story scope explicitly adds live HTTP.
- **Observability:** `get_pipeline_logger("pharma_rd.agents.consumer")`; `extra` includes distinct `event` name for demand/unmet-need.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Config | `pharma_rd/pharma_rd/config.py` |
| Agent | `pharma_rd/pharma_rd/agents/consumer.py` |
| Integration | `pharma_rd/pharma_rd/integrations/` (new module, e.g. `market_demand.py` or `unmet_need_demand.py`) |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` (if new log fields) |
| Tests | `pharma_rd/tests/agents/test_consumer.py`, `pharma_rd/tests/pipeline/test_contracts.py`, `pharma_rd/tests/pipeline/test_logging.py` |
| Fixtures | `pharma_rd/tests/fixtures/...` (e.g. `unmet_need_demand/sample.json`) |
| Docs | `pharma_rd/README.md`, `pharma_rd/.env.example` |

### Previous story intelligence (5.1 / 5.2)

- **Schema evolution:** Each story bumped `schema_version` (v2 → v3); follow with **v4** and document for Epic 6 consumers.
- **`_resolve_config_path` duplication** across integration modules — **defer** shared util unless already consolidated; do not block FR13 on refactor.
- **Review-hardening:** Prefer explicit JSON messages for `null` vs missing keys (see 5.1 `feedback_themes`); **period** typing coercion lessons from 5.2 (`pharmacy_sales`) — coerce display-safe types where needed, avoid `bool`/`int` confusion for subclasses.
- **Practice/mock:** FR26 is primarily about consumer **feedback** practice mock; for FR13, if product expects a **practice placeholder** when unset, align with PM intent — **minimum** is NFR-I1 transparency (explicit insufficient-signal wording), not necessarily a built-in mock list.

### Testing requirements

- Pydantic JSON round-trip for `ConsumerOutput` at v4 after schema change.
- Agent tests: temp fixtures / patched settings; cover **unconfigured** (explicit FR13 gap text), **configured empty/invalid**, **happy path** with at least one signal + source.
- Ruff E501 (88) on new strings/docstrings.

### Latest tech / deps

- **Pydantic v2** + existing project stack — no new dependencies required for fixture-based MVP.
- If adding optional HTTP later, use **`httpx`** with existing timeout/retry settings — **out of scope** unless you extend the story during implementation with PM approval.

### Git / repo context

- Recent commits on `main` are pre–Epic 5 bulk work; **use current tree** (`consumer.py`, `contracts.py`, integrations) as source of truth for patterns.

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`ConsumerOutput` schema v4** with **`UnmetNeedDemandSignalItem`** (`signal`, `summary`, **`source`**).
- **`integrations/unmet_need_demand.py`** — fixture load for `unmet_need_demand_signals`; NFR-I1 gaps for missing/null/non-array root key.
- **`consumer_unmet_need_demand`** log event with **`unmet_need_demand_count`**; **`logging_setup`** extended.
- When demand path unset: **`integration_notes`** include FR13 + `PHARMA_RD_UNMET_NEED_DEMAND_PATH` hint; practice-mock test asserts alongside FR12.
- **`tests/fixtures/unmet_need_demand/sample.json`** for happy-path tests.
- Ruff E501: shortened **`test_competitor.py`** docstring so **`ruff check`** passes (pre-existing line length).

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/agents/consumer.py`
- `pharma_rd/pharma_rd/integrations/unmet_need_demand.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_consumer.py`
- `pharma_rd/tests/agents/test_competitor.py`
- `pharma_rd/tests/fixtures/unmet_need_demand/sample.json`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Story 5.3 implemented — FR13 unmet need / demand signals, schema v4, tests, docs; sprint → review.
- 2026-04-05: Code review — `run_consumer` docstring FR13; defer `_resolve_config_path` consolidation; sprint → done.

---

**Story completion status:** done — Code review complete; docstring patch applied; defer recorded.

## References

- Epic 5 / Story 5.3: `_bmad-output/planning-artifacts/epics.md`
- PRD FR13: `_bmad-output/planning-artifacts/prd.md` (Consumer & market insight)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — integrations, stage order, NFRs
- Prior artifacts: `_bmad-output/implementation-artifacts/5-1-consumer-feedback-signals.md`, `_bmad-output/implementation-artifacts/5-2-pharmacy-sales-trend-signals-when-configured.md`

---

### Questions / clarifications (optional before dev)

- If **both** fixture path and future HTTP exist, precedence order should be documented in README (fixtures only for MVP is fine).
