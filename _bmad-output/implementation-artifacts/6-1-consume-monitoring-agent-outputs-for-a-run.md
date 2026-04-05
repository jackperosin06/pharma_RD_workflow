# Story 6.1: Consume monitoring agent outputs for a run

Status: done

## Story

As a **workflow operator**,
I want **Synthesis to load Clinical, Competitor, and Consumer outputs for the same run**,
so that **ranking uses a single coherent snapshot** (FR14).

## Acceptance Criteria

1. **Given** prior stages persisted outputs for **run_id**  
   **When** the Synthesis stage runs  
   **Then** it **fails fast** with a **clear error** if any **required** upstream artifact is **missing** (e.g. file not on disk under the artifact root)  
   **And** when upstream is **partial** (artifacts exist but upstream stages reported gaps in structured output), synthesis **proceeds** with **documented gaps** (NFR-I1)

## Tasks / Subtasks

- [x] **Runner handoff** — In `pharma_rd/pipeline/runner.py` `_execute_stage` for `stage_key == "synthesis"`, load and validate **three** artifacts for the same `run_id`: **`clinical`**, **`competitor`**, **`consumer`** (use `read_artifact_bytes` + `ClinicalOutput` / `CompetitorOutput` / `ConsumerOutput.model_validate_json`). Pass all three into `run_synthesis`. Do **not** rely on Consumer alone for FR14.
- [x] **Missing artifact behavior** — If a file is missing or unreadable before validation, raise a **single clear error** (include `run_id`, stage key, and resolved path hint). Map `FileNotFoundError` / OSError to an operator-friendly message; avoid raw tracebacks in normal operator flows (align with existing pipeline failure handling).
- [x] **Synthesis agent** — Update `pharma_rd/agents/synthesis.py`: `run_synthesis(run_id, clinical, competitor, consumer)` — assert or validate **`run_id`** consistency across all three models (fail fast with a clear message if mismatched — indicates corrupt handoff).
- [x] **Contract (minimal)** — Extend `SynthesisOutput` as needed for FR14 snapshot accountability: e.g. bump **`schema_version`** to **2**; include **`run_id`**; include a field that **records** upstream was loaded (e.g. upstream **`schema_version`** numbers or a short **snapshot note**); include **`synthesis_gaps`** or **`aggregated_upstream_gaps`** (list of strings) that **merge** or reference `data_gaps` from Clinical / Competitor / Consumer when non-empty so NFR-I1 partial runs are visible in synthesis JSON. Keep `extra="forbid"`. Update `tests/pipeline/test_contracts.py` round-trip.
- [x] **Partial upstream (NFR-I1)** — When all three artifacts exist and parse, but any upstream lists are empty or `data_gaps` / `integration_notes` are non-empty, **still complete** the stage and persist synthesis output with **transparent** aggregated gap text (do not fail solely because upstream reported integration gaps).
- [x] **Logging** — Replace or supplement `log_agent_stub` for synthesis with at least one structured line (e.g. event name, counts of upstream gap lines or a `snapshot_ok` flag) consistent with other agents; extend `logging_setup` JSON allowlist if new `extra` keys are added.
- [x] **Tests** — Add/extend tests: (1) full pipeline still completes and synthesis receives three inputs; (2) missing clinical/competitor/consumer artifact causes **fail-fast** with message assertion; (3) synthetic or patched scenario where upstream `data_gaps` exist — synthesis output documents them. Prefer `tests/agents/test_synthesis.py` and/or `tests/pipeline/` integration tests mirroring existing patterns.
- [x] **Resume / retry** — If `run_pipeline_resume_from` or stage retry paths assume the old `run_synthesis` signature, update them to match (search `synthesis` / `run_synthesis` across `pharma_rd/`).

### Review Findings

- [x] [Review][Patch] **`read_stage_artifact_model` error wording** — [`pharma_rd/pharma_rd/persistence/artifacts.py`] — Wrapped **`ValidationError`** previously labeled “Invalid JSON” even when failure was schema/shape-related; garbled binary surfaced as generic JSON error. **Resolved:** raise **`ValueError`** with **“Artifact validation failed …”**; added **`test_read_stage_artifact_model_garbled_bytes`**.

- [x] [Review][Defer] **Friendly artifact errors only on synthesis path** — Clinical/competitor/consumer stages still use **`read_artifact_bytes`** + **`model_validate_json`** without the shared helper — pre-existing; optional unify when touching runner again.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| FR14 | Single-run snapshot: Clinical + Competitor + Consumer all in synthesis |
| NFR-I1 | Partial upstream → proceed with **documented** gaps in synthesis output |
| NFR-R1 | Clear `error_summary` / operator-visible failure when artifact missing |

### Architecture compliance

- **Artifact layout:** `{artifacts_root}/{run_id}/{stage}/output.json` — unchanged.
- **Ordering:** Synthesis runs after consumer; all prior stage artifacts must exist for a normal full run.
- **Downstream:** Delivery still consumes `SynthesisOutput` only — Epic 7 may later depend on richer fields; keep schema evolution **additive** where possible.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Runner | `pharma_rd/pharma_rd/pipeline/runner.py` |
| Synthesis agent | `pharma_rd/pharma_rd/agents/synthesis.py` |
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` (if new fields) |
| Tests | `pharma_rd/tests/pipeline/test_contracts.py`, new or extended synthesis/pipeline tests |
| Docs | `pharma_rd/README.md` — FR14 / synthesis input snapshot (short) |

### Previous story intelligence (Epic 5 / 5-3)

- **ConsumerOutput** is **schema v4** with `unmet_need_demand_signals` — synthesis must accept full `ConsumerOutput` validation.
- **CompetitorOutput** v4 / **ClinicalOutput** v2 — use `model_validate_json` on bytes from disk; same pattern as current consumer-only load.

### Testing requirements

- Contract round-trip for `SynthesisOutput` after schema change.
- No regression: default pipeline run completes all five stages.
- Ruff E501 (88) on new strings.

### Latest tech / deps

- No new runtime dependencies expected (stdlib + Pydantic + existing layout).

## Dev Agent Record

### Agent Model Used

Composer (Cursor)

### Debug Log References

### Completion Notes List

- **`read_stage_artifact_model`** in `persistence/artifacts.py` — clear **`FileNotFoundError`** / **`OSError`** / **`ValueError`** (invalid JSON) messages with `run_id`, `stage`, path.
- **`SynthesisOutput` schema v2** — `run_id`, upstream schema version ints, **`aggregated_upstream_gaps`** (prefixed `data_gaps` + `integration_notes` per stage).
- **`synthesis_upstream_snapshot`** log event — **`upstream_gap_count`**, **`snapshot_ok`**; synthesis no longer uses **`log_agent_stub`** (delivery still does).
- **`run_synthesis(run_id, clinical, competitor, consumer)`** — **`run_id`** mismatch → **`ValueError`**.

### File List

- `pharma_rd/pharma_rd/persistence/artifacts.py`
- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/tests/persistence/test_artifacts_read_model.py` (incl. post-review garbled-bytes case)
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/tests/pipeline/test_contracts.py` (implicit via `SynthesisOutput()` defaults)
- `pharma_rd/README.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-06: Story 6.1 implemented — FR14 three-way snapshot, `SynthesisOutput` v2, tests, README; sprint → review.
- 2026-04-06: Code review — `read_stage_artifact_model` message clarity + garbled-bytes test; defer runner error-message consistency; sprint → done.

---

**Story completion status:** done — Code review complete; patch applied; defer logged.

## References

- Epic 6 / Story 6.1: `_bmad-output/planning-artifacts/epics.md`
- PRD FR14: `_bmad-output/planning-artifacts/prd.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — pipeline stages, integrations
- Prior consumer / schema context: `_bmad-output/implementation-artifacts/5-3-unmet-need-and-demand-signals.md`

---

### Optional questions before dev

- If product prefers **runner** to stay thin: alternative is `run_synthesis(artifact_root, run_id)` loading inside the agent — either is acceptable if FR14 and tests are satisfied; **current story assumes runner loads and passes models** for consistency with competitor/consumer stages.
