# Story 8.1: Therapeutic area scope configuration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **to configure therapeutic area scope and boundaries with clear validation**,
so that **Clinical and downstream stages read the same validated scope model** and **misconfiguration fails fast with operator-readable errors** (FR23).

## Acceptance Criteria

1. **Given** **`PHARMA_RD_THERAPEUTIC_AREAS`** (or equivalent **`Settings.therapeutic_areas`**) is loaded from the environment  
   **When** settings are constructed (application startup / first **`get_settings()`**)  
   **Then** the value is **validated** so that **invalid** scope strings **fail at load time** with a **clear `ValueError` or Pydantic validation message** (no secrets in the message) listing what is wrong (e.g. empty segment, label too long, too many labels, disallowed characters).

2. **Given** a **valid** therapeutic-area configuration  
   **When** code calls **`Settings.therapeutic_area_labels()`** (or the canonical accessor used by agents)  
   **Then** the returned list matches **normalized** comma-separated parsing: **trimmed** labels, **no empty** entries, **stable ordering** preserved as in the env string (left-to-right), and the **same list** is what **Clinical**, **Synthesis**, **Delivery/Slack** (scan summary), and any other consumer should use—**no second divergent parser** for TA labels in MVP.

3. **Given** **`therapeutic_areas`** is **empty** (unset or whitespace-only after trim)  
   **When** settings validate  
   **Then** configuration is **accepted** as **“no TA scope”** consistent with **NFR-I1** / existing behavior (Clinical completes with explicit **data_gaps** / notes)—**do not** require a non-empty list for practice mode.

4. **Given** **invalid** configuration  
   **When** an operator runs **`pharma-rd`** commands that load settings (e.g. **`run`**, **`runs`**, **`status`**)  
   **Then** the process **exits non-zero** with the validation error on **stderr** (or the project’s established error path)—document the behavior in **`pharma_rd/README.md`**.

5. **Given** **CI**  
   **When** tests run  
   **Then** unit tests cover **at least**: valid multi-label string, empty scope, and **representative invalid** cases (e.g. over-long label, empty token between commas if rejected, disallowed character class if defined).

## Tasks / Subtasks

- [x] **Rules & caps** — Define explicit MVP validation rules in code comments + README (e.g. max **labels**, max **characters per label**, allowed character class such as **letters, digits, spaces, hyphen, underscore**—pick conservative defaults; reject control characters and commas **inside** a label except as delimiter).

- [x] **`pharma_rd/pharma_rd/config.py`**:
  - [x] Add **`field_validator`** and/or **`model_validator`** on **`Settings`** for **`therapeutic_areas`** so invalid values **raise** before agents run.
  - [x] Ensure **`therapeutic_area_labels()`** returns the **normalized** list from validated input (reuse existing method signature; extend implementation if needed).
  - [x] Keep **`@lru_cache` on `get_settings()`** behavior: failed validation must **clearly** fail when settings are first loaded (no silent cache of bad config).

- [x] **Consumers** — Audit call sites (**Clinical**, **Synthesis** scan lines, **Slack** notification, etc.): they must use **`get_settings().therapeutic_area_labels()`** (or pass **`Settings`** through)—**remove** any ad-hoc splitting of **`therapeutic_areas`** if present.

- [x] **Tests** — **`pharma_rd/tests/`** (e.g. **`test_config.py`** or **`tests/config/test_therapeutic_areas.py`**):
  - [x] Valid strings; empty; invalid strings; monkeypatch env + **`get_settings.cache_clear()`** pattern used elsewhere.

- [x] **README + `.env.example`** — Document FR23 validation, caps, and that **empty** means no TA scope; example valid line.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR23** | TA scope and boundaries—validated configuration model. |
| **NFR-I1** | Empty scope remains a valid “not configured” outcome. |
| **NFR-R1** | Clear errors for operators when config is wrong. |

### Architecture compliance

- **Configuration** lives in **`pharma_rd.config.Settings`** (existing **`PHARMA_RD_`** prefix, **`pydantic-settings`**) [Source: `_bmad-output/planning-artifacts/architecture.md` — configuration vs code].
- **No new persistence table** required for this story unless product expands scope registry later.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Config | `pharma_rd/pharma_rd/config.py` |
| Consumers | `pharma_rd/pharma_rd/agents/clinical.py`, `pharma_rd/pharma_rd/agents/synthesis.py`, `pharma_rd/pharma_rd/integrations/slack_insight_notification.py` (audit only) |
| Tests | `pharma_rd/tests/...` |
| Docs | `pharma_rd/README.md`, `pharma_rd/.env.example` |

### Previous story intelligence (Epic 7 / config patterns)

- **`Settings.therapeutic_area_labels()`** already exists; **`therapeutic_areas`** is a comma-separated string.
- **Today:** **`clinical.py`** already calls **`therapeutic_area_labels()`**; **`synthesis`** reads **`ClinicalOutput.therapeutic_areas_configured`**; **Slack** uses **`settings.therapeutic_area_labels()`** — tightening **`Settings`** validation applies everywhere; grep for **`split(",")`** on **`therapeutic_areas`** outside **`config.py`** (should be none).
- **`get_settings.cache_clear()`** in tests when env changes.
- Follow **Ruff** line length **88**; **Python 3.12**.

### Technical requirements (guardrails)

- **Pydantic v2** validators; messages must **not** echo full env files or secrets.
- **Backward compatibility:** existing **valid** env strings used in tests and README examples must still parse after validation tightens.

### Project structure notes

- Package **`pharma_rd.pharma_rd`**; flat layout under `pharma_rd/pharma_rd/`.

### Git intelligence

- Small, focused commits: validation + tests + docs.

### Latest tech / deps

- No new dependencies; stdlib + Pydantic only.

## Dev Agent Record

### Agent Model Used

Cursor (AI coding agent)

### Debug Log References

### Completion Notes List

- Added `_normalize_and_validate_therapeutic_areas` with caps (32 labels, 128 chars/label), Unicode `\w`/space/hyphen pattern, rejection of empty comma segments; `field_validator` on `therapeutic_areas`; stored value is normalized comma–space joined string.
- `main()` catches `ValidationError`, prints to stderr, exits 1 so `pharma-rd` fails fast on bad env.
- Tests in `test_config.py` (valid/empty/invalid cases) and `test_cli.py` (exit 1 on bad TA env).
- README and `.env.example` document FR23; consumer audit: only `config.therapeutic_area_labels()` splits; clinical/synthesis/slack use accessor or clinical artifact lists.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/main.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/tests/test_cli.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/8-1-therapeutic-area-scope-configuration.md`

### Change Log

- 2026-04-05: Story 8.1 implementation — TA validation, CLI error path, tests, docs, sprint status → review.
- 2026-04-05: Code review — no patch items; 2 deferrals recorded; status → done.

## References

- Epic 8 / Story 8.1: `_bmad-output/planning-artifacts/epics.md`
- FR23: `_bmad-output/planning-artifacts/prd.md`
- Architecture — configuration: `_bmad-output/planning-artifacts/architecture.md`
- Current settings: `pharma_rd/pharma_rd/config.py` — **`therapeutic_areas`**, **`therapeutic_area_labels()`**

---

**Story completion status:** done — code review complete (2026-04-05)

### Review Findings

- [x] [Review][Defer] Verbose `ValidationError` text on stderr — `pharma_rd/pharma_rd/main.py:115` — deferred: printing `str(e)` can be multi-line; acceptable for operators; optional follow-up to emit a single-line summary from `e.errors()`.

- [x] [Review][Defer] Mixed-scope branch changes — `sprint-status.yaml`, `README.md`, `config.py`, `.env.example` — deferred, pre-existing: Epic 5–7 documentation and settings appear alongside FR23; prefer separate commits or PR slices for traceability in future work.
