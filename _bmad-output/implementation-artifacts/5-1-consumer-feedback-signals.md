# Story 5.1: Consumer feedback signals

Status: done

<!-- Optional: run validate-create-story before dev-story. -->

## Story

As a **workflow operator**,
I want **consumer feedback processed from configured sources**,
so that **market voice informs synthesis** (FR11).

## Acceptance Criteria

1. **Given** configured consumer sources (may be mock)  
   **When** the Consumer stage runs  
   **Then** structured output includes **feedback themes** with **sources**  
   **And** mock mode is **explicit** in configuration and output when used (FR26 alignment)

## Tasks / Subtasks

- [x] **Contract** — Extend `ConsumerOutput`: bump `schema_version`, add typed list(s) for feedback themes (e.g. theme/summary + source reference), optional `run_id` if aligned with `CompetitorOutput`; `data_gaps` / `integration_notes` as needed for NFR-I1; keep `extra="forbid"`. Update `tests/pipeline/test_contracts.py` round-trip.
- [x] **Configuration** — Add `PHARMA_RD_*` settings in `pharma_rd/config.py` for consumer feedback (e.g. optional JSON fixture path, practice/mock flag, max file bytes guardrail). Document in `.env.example`; no secrets in repo (NFR-S1).
- [x] **Integration / fixture path** — Prefer `pharma_rd/integrations/` module for loading JSON fixture(s) (mirror `regulatory_signals` / competitor patterns): bounded read, clear errors, empty/partial handling with transparency (NFR-I1).
- [x] **Agent** — Replace stub body in `pharma_rd/agents/consumer.py`: call `ensure_connector_probe("consumer")`, use `get_settings()`, merge fixture + explicit notes; when using mock/public stub, state **practice/mock** in structured output and/or `integration_notes` (FR26).
- [x] **Logging** — Structured JSON logs with consistent `event` names (e.g. consumer feedback count / outcome); include `run_id` in message context where other agents do.
- [x] **Tests** — Add `tests/agents/test_consumer.py` (and fixture JSON under `tests/fixtures/` if used); extend logging tests if new events are introduced.
- [x] **Docs** — `pharma_rd/README.md`: FR11 behavior, env vars, practice vs configured feeds.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| FR11 | Feedback themes + sources in Consumer stage output |
| FR26 | Practice/mock must be explicit in configuration and output |
| NFR-I1 | Degrade gracefully: empty/partial feeds → explicit gaps, stage still completes |
| NFR-I2 | Classify integration failures in logs where HTTP is used |
| Architecture | Pydantic v2, `get_settings()` only, snake_case JSON, ISO 8601 timestamps |

### Architecture compliance

- **Stage handoff:** Consumer reads `CompetitorOutput` from disk (already wired in `runner.py`); do not change pipeline order.
- **Schema evolution:** Increment `ConsumerOutput.schema_version` when adding fields; document breaking vs additive changes in dev notes for Epic 6 consumers.
- **Settings:** All new env vars via `Settings` in `config.py` with `PHARMA_RD_` prefix and validators for “empty string means None” where appropriate (match `competitor_regulatory_path` pattern).
- **Observability:** Reuse `get_pipeline_logger("pharma_rd.agents.consumer")`; structured `extra` dicts with `event`, `outcome`, counts.

### Project structure notes

- App root: `pharma_rd/pharma_rd/` (not `src/` — current repo layout).
- Tests mirror packages: `tests/agents/`, `tests/pipeline/`, `tests/fixtures/`.
- CI: `uv run ruff check .` and `uv run pytest` from `pharma_rd/`.

### Previous story intelligence (Epic 4 / 4-3)

- **Competitor agent** demonstrates: `ensure_connector_probe`, `get_settings()`, fixture ingestion with caps, `data_gaps` + `integration_notes`, schema version bumps, README + `.env.example` updates.
- **Downstream:** `SynthesisOutput` is still stub — do not implement synthesis consumption here; only ensure `ConsumerOutput` is stable and versioned for a later epic.

### File structure requirements (expected touch list)

| Area | Paths |
|------|--------|
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Config | `pharma_rd/pharma_rd/config.py` |
| Agent | `pharma_rd/pharma_rd/agents/consumer.py` |
| Integration (new or extend) | `pharma_rd/pharma_rd/integrations/` — e.g. `consumer_feedback.py` if non-trivial parsing stays out of the agent |
| Tests | `pharma_rd/tests/agents/test_consumer.py`, `pharma_rd/tests/pipeline/test_contracts.py`, optional `pharma_rd/tests/pipeline/test_logging.py` |
| Fixtures | `pharma_rd/tests/fixtures/...` |
| Docs | `pharma_rd/README.md`, `pharma_rd/.env.example` |

### Testing requirements

- Contract JSON round-trip for `ConsumerOutput` after schema change.
- Agent tests: mock settings or temp fixture files; cover “configured mock”, “not configured” (explicit gaps), and at least one happy path with themes + sources.
- Keep line length within Ruff E501 (88) on docstrings and strings.

### References

- Epic 5 / Story 5.1: `_bmad-output/planning-artifacts/epics.md` (Consumer Insight Agent)
- Architecture patterns: `_bmad-output/planning-artifacts/architecture.md` — Implementation patterns and consistency rules
- Prior art: `_bmad-output/implementation-artifacts/4-3-patent-filing-flags.md` (competitor output versioning and fixtures)

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`ConsumerOutput` schema v2** with **`ConsumerFeedbackThemeItem`**, **`practice_mode`**, **`data_gaps`**, **`integration_notes`**.
- **`integrations/consumer_feedback.py`** — fixture file/dir ingest with byte cap and NFR-I1 gap messages.
- **`consumer_feedback` log event** with **`feedback_theme_count`** and **`practice_mode`**; **`logging_setup`** extended for JSON line fields.
- Default **practice mock** when path unset; **`PHARMA_RD_PRACTICE_CONSUMER_MOCK=false`** with no path yields gaps only.
- Pipeline logging test: **`agent_stub`** now **2** (synthesis, delivery); **`consumer_feedback`** asserted.

### File List

- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/agents/consumer.py`
- `pharma_rd/pharma_rd/integrations/consumer_feedback.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_consumer.py`
- `pharma_rd/tests/fixtures/consumer_feedback/sample.json`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Story 5.1 implemented — FR11 consumer feedback themes, schema v2, fixtures, tests, docs.
- 2026-04-05: Code review — `feedback_themes` null/missing gap message in `consumer_feedback.py`; `test_fixture_null_feedback_themes`.

### Review Findings

- [x] [Review][Patch] Clarify `feedback_themes` gap message when JSON value is `null` — [`pharma_rd/pharma_rd/integrations/consumer_feedback.py`](pharma_rd/pharma_rd/integrations/consumer_feedback.py) uses `data.get("feedback_themes")`; both missing key and `"feedback_themes": null` hit the same branch, but the message says the file has “no … array”, which is misleading for `null`. Prefer wording such as “missing, null, or not an array” before the list check. **Resolved:** message now states missing or null with expected array shape; `test_fixture_null_feedback_themes` added.

- [x] [Review][Defer] Duplicate `_resolve_config_path` helper vs `regulatory_signals.py` [`pharma_rd/pharma_rd/integrations/consumer_feedback.py:14`] — deferred, pre-existing pattern; optional shared util in a later refactor.

- [x] [Review][Defer] Unrelated docstring shortening in `test_competitor.py` bundled with this work [`pharma_rd/tests/agents/test_competitor.py:157`] — deferred; Ruff E501 fix, not part of FR11 scope.

---

**Story completion status:** done — Review patch applied; sprint synced.
