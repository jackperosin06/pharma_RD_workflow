# Story 8.2: Competitor watchlists and identifiers

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **competitor watchlists with keywords or identifiers validated and normalized in configuration**,
so that **the Competitor stage and downstream consumers read the same scope model** and **misconfiguration fails fast with operator-readable errors**, while **empty watchlist remains an explicit, visible “not configured” path** for practice mode (FR24, NFR-I1).

## Acceptance Criteria

1. **Given** **`PHARMA_RD_COMPETITOR_WATCHLIST`** (or **`Settings.competitor_watchlist`**) is loaded from the environment  
   **When** **`Settings`** is constructed (first **`get_settings()`**)  
   **Then** the value is **validated** so that **invalid** strings **fail at load time** with a **clear `ValueError` or Pydantic validation message** (no secrets) explaining the problem (e.g. empty segment between commas, label too long, too many labels, disallowed characters).

2. **Given** a **valid** non-empty watchlist configuration  
   **When** code calls **`Settings.competitor_labels()`**  
   **Then** the returned list matches **normalized** comma-separated parsing: **trimmed** labels, **no empty** entries, **stable left-to-right order**, and this accessor is the **canonical** list for **Competitor**, **Synthesis**, **Slack** scan summaries, and any other consumer—**no ad-hoc splitting** of **`competitor_watchlist`** outside **`config.py`**.

3. **Given** **`competitor_watchlist`** is **empty** (unset or whitespace-only after trim)  
   **When** settings validate  
   **Then** configuration is **accepted** as **“no competitor watchlist”** consistent with **NFR-I1** — the Competitor stage may still complete with **explicit `data_gaps` / `integration_notes`** (existing behavior). **Do not** require a non-empty list for practice mode at settings load.

4. **Given** **invalid** non-empty configuration (validation failure)  
   **When** an operator runs **`pharma-rd`** commands that load settings (same pattern as Story **8.1**)  
   **Then** the process **exits non-zero** and prints the validation error on **stderr** — document in **`pharma_rd/README.md`** and **`pharma_rd/.env.example`**.

5. **Given** **CI**  
   **When** tests run  
   **Then** unit tests cover **at least**: valid multi-label string, empty watchlist, and **representative invalid** cases (e.g. over-long label, empty token between commas, disallowed character if defined).

6. **Given** Epic **8.2** product wording (“keywords or identifiers”)  
   **When** choosing allowed character classes and caps  
   **Then** document the rules in code comments + README (e.g. max labels, max chars per label). Prefer **consistency** with Story **8.1** TA rules **unless** competitor/corporate naming requires extra characters (e.g. **`&`**, **`.`**, parentheses); if you extend the charset, justify in comments and keep **commas** as the **only** delimiter between labels.

## Tasks / Subtasks

- [x] **Rules & caps** — Define MVP validation rules in code + README: max labels, max length per label, allowed characters (corporate names / identifiers). Optionally factor shared trimming/normalization logic with **`_normalize_and_validate_therapeutic_areas`** to avoid drift, or mirror with a dedicated **`_normalize_and_validate_competitor_watchlist`** and shared constants.

- [x] **`pharma_rd/pharma_rd/config.py`**:
  - [x] Add **`field_validator`** on **`competitor_watchlist`** (mode **`after`**) calling the normalizer; store **normalized** comma–space joined string (same storage pattern as **`therapeutic_areas`**).
  - [x] Ensure **`competitor_labels()`** returns the list derived from **validated** stored value only.
  - [x] **`get_settings()`** remains **`@lru_cache`** — failed validation must raise when settings are first loaded (no cached bad config).

- [x] **Consumers** — Audit: **`competitor.py`**, **`synthesis`**, **`slack_insight_notification`**, **`regulatory_signals`** strings — must use **`competitor_labels()`** or **`Settings`**; remove any **`competitor_watchlist.split`** outside **`config.py`** if present.

- [x] **CLI** — Reuse Story **8.1** behavior: **`main()`** already catches **`ValidationError`**; confirm invalid watchlist triggers it when settings load (add test if missing).

- [x] **Tests** — **`pharma_rd/tests/test_config.py`** (and **`test_cli.py`** if needed): monkeypatch **`PHARMA_RD_COMPETITOR_WATCHLIST`**, **`get_settings.cache_clear()`**, cases analogous to TA tests.

- [x] **README + `.env.example`** — Document FR24 validation, caps, empty = no watchlist / gaps path, failure on bad env.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR24** | Competitor watchlists and related keywords or identifiers — configuration, not code. |
| **NFR-I1** | Empty / not configured remains valid; explicit gaps in output. |
| **NFR-R1** | Clear errors when configuration is malformed. |
| **Epics.md §8.2** | “Only configured competitors”; empty watchlist “rejected **or** handled with **explicit** operator warning” — MVP uses **handled with explicit gaps/notes** when empty; **reject** applies to **invalid** formatted strings at load. |

### Architecture compliance

- **Configuration** in **`pharma_rd.config.Settings`** with **`PHARMA_RD_`** prefix and **`pydantic-settings`** [Source: `_bmad-output/planning-artifacts/architecture.md` — configuration vs code].
- No new persistence tables required for this story.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Config | `pharma_rd/pharma_rd/config.py` |
| Consumers | `pharma_rd/pharma_rd/agents/competitor.py`, `pharma_rd/pharma_rd/agents/synthesis.py`, `pharma_rd/pharma_rd/integrations/slack_insight_notification.py`, `pharma_rd/pharma_rd/integrations/regulatory_signals.py` (audit only) |
| CLI | `pharma_rd/pharma_rd/main.py` (likely unchanged if **`ValidationError`** already global) |
| Tests | `pharma_rd/tests/test_config.py`, `pharma_rd/tests/test_cli.py` |
| Docs | `pharma_rd/README.md`, `pharma_rd/.env.example` |

### Previous story intelligence (8.1)

- **`_normalize_and_validate_therapeutic_areas`**, **`therapeutic_areas_validated`**, **`therapeutic_area_labels()`** — copy patterns for competitor watchlist; keep error messages free of secrets.
- **`main()`**: **`except ValidationError`** → stderr → **`SystemExit(1)`**.
- Tests: **`ValidationError`** match substrings; CLI test for exit **1** on bad env.
- **Ruff** line length **88**; **Python 3.12**.

### Technical requirements (guardrails)

- **Pydantic v2** validators.
- **Backward compatibility:** existing **valid** env examples in README/tests must still parse after validation tightens.
- **Grep** for **`split(",")`** on **`competitor_watchlist`** outside **`config.py`** and eliminate ad-hoc parsers.

### Project structure notes

- Package **`pharma_rd.pharma_rd`**; flat layout under `pharma_rd/pharma_rd/`.

### Git intelligence

- Recent commits on `main` are pre–Epic 8 uncommitted work; follow existing **`pharma_rd`** conventions and small focused diffs.

### Latest tech / deps

- No new dependencies; **stdlib** + **Pydantic** only (same as Story **8.1**).

## Dev Agent Record

### Agent Model Used

Cursor (AI coding agent)

### Debug Log References

### Completion Notes List

- Added **`_normalize_and_validate_competitor_watchlist`** with same caps as FR23 (32 / 128), regex **`[\w\s\-&.,()]+`** for corporate identifiers; **`competitor_watchlist_validated`** field validator; normalized storage string.
- Extended **`test_config.py`** (empty, multi-label, corporate chars, invalid segment/char/length/count); **`test_cli.py`** invalid watchlist exit **1**.
- README Epic 8 FR24 bullet and `.env.example` comment; consumer audit: only **`config.competitor_labels()`** splits **`competitor_watchlist`**.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/tests/test_cli.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/8-2-competitor-watchlists-and-identifiers.md`

### Change Log

- 2026-04-06: Story 8.2 — FR24 competitor watchlist validation, tests, docs; sprint → review.
- 2026-04-06: Code review — no patch/decision items; deferrals recorded; status → done.

## References

- Epic 8 / Story 8.2: `_bmad-output/planning-artifacts/epics.md`
- FR24: `_bmad-output/planning-artifacts/prd.md`
- Story 8.1 (pattern reference): `_bmad-output/implementation-artifacts/8-1-therapeutic-area-scope-configuration.md`
- Current settings: `pharma_rd/pharma_rd/config.py` — **`competitor_watchlist`**, **`competitor_labels()`**

---

**Story completion status:** done — code review complete (2026-04-06)

### Review Findings

- [x] [Review][Defer] Near-duplicate normalization vs FR23 — `pharma_rd/pharma_rd/config.py` — deferred: `_normalize_and_validate_competitor_watchlist` mirrors therapeutic-area logic; optional future refactor to a shared helper with per-field regex/env-key parameters to reduce drift.

- [x] [Review][Defer] Apostrophe and other punctuation in corporate names — `config.py` (`_COMPETITOR_LABEL_RE`) — deferred: labels like `O'Brien` or `L'Oréal` may fail the current charset; extend regex or document as known MVP limitation if operators report real configs.

- [x] [Review][Defer] Mixed-scope working tree — `sprint-status.yaml`, `config.py`, `README.md` — deferred, pre-existing: same branch may carry non–8.2 edits; use narrower commits when traceability matters.
