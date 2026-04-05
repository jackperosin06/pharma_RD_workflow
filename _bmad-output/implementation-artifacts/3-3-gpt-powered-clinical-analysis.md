# Story 3.3: GPT-powered clinical analysis

Status: done

## Story

As a **workflow operator**,
I want **the Clinical stage to send fetched PubMed/publication material to GPT-4o for analyst-grade interpretation**,
So that **summaries reflect what is clinically significant, relevant to configured therapeutic areas, and which trials deserve iNova priority attention** (extends FR6).

## Acceptance Criteria

1. **Given** the Clinical agent has **completed publication fetch** (existing FR6 path) for a run  
   **When** **`PHARMA_RD_OPENAI_API_KEY`** (or agreed env name) is **set**  
   **Then** the stage **calls OpenAI** (default model **gpt-4o**, configurable) with a **system prompt** that positions the model as a **pharma R&D analyst** and includes **configured therapeutic area labels** from settings  
   **And** the **user** message contains the **structured publication payload** (titles, summaries, references—no secrets) sufficient for analysis  

2. **Given** a successful model response  
   **When** the response is merged into **`ClinicalOutput`**  
   **Then** structured output includes **GPT-derived fields** (e.g. analyst summary, TA relevance assessment, **prioritized trials / attention list**) in a **Pydantic-safe** shape **versioned** in `schema_version` or extension fields per team convention  
   **And** original **fetched publication rows** remain **preserved** for traceability (NFR-I1)  

3. **Given** the OpenAI call **fails** (auth, rate limit, timeout) or the key is **unset**  
   **When** the Clinical stage completes  
   **Then** behavior is **explicit**: either **degrade** to pre-3.3 deterministic summaries with **`integration_notes` / `data_gaps`** explaining the skip, or **fail the stage** with an **actionable** error—**document the chosen policy** in README (NFR-R1, NFR-I2)  

4. **Given** **CI** and **local tests**  
   **When** tests run  
   **Then** **no real API key** is required: OpenAI client is **mocked** or uses **recorded fixtures**; prompts and responses **never** logged with full content at **DEBUG** if that could leak MNPI (NFR-S1, NFR-S4 assumption: non-PHI practice data)  

## Tasks / Subtasks

- [x] Add **`openai`** (official SDK) dependency; wire **`Settings`** for API key, model id, timeout (NFR-P3 alignment).  
- [x] Implement **`clinical.py`** (or submodule) post-fetch GPT step with **system + user** prompts; inject **TA scope** from config.  
- [x] Extend **`ClinicalOutput`** (or companion model) for analyst fields; bump **`schema_version`** if needed; migration notes for old artifacts.  
- [x] Tests: mock OpenAI; happy path + timeout + missing key degradation path.  
- [x] **`README.md`** + **`.env.example`**: document **`PHARMA_RD_OPENAI_API_KEY`**, model override, and operational behavior when unset.  

## Dev Notes

- **Sequencing:** Implement **after** 3.1/3.2 behavior is stable; downstream **6.5** will consume richer clinical signal.  
- **iNova** naming in prompts is **example narrative**; make org name **configurable** if required for white-label.  
- Prefer **JSON mode** / **structured outputs** if the API supports it, to simplify parsing.  

## References

- FR6, NFR-I1, NFR-I2, NFR-P3, NFR-R1, NFR-S1, NFR-S4  
- `pharma_rd/pharma_rd/agents/clinical.py`, `pharma_rd/pharma_rd/pipeline/contracts.py`  

## Dev Agent Record

### Agent Model Used

Cursor (implementation agent)

### Debug Log References

### Completion Notes List

- **Code review (2026-04-05):** `internal_research` structured log moved before `_apply_clinical_gpt`; `call_clinical_gpt_analysis` returns a controlled error when `resp.choices` is empty.

- **`ClinicalGptAnalysis`** + optional **`clinical_gpt_analysis`** on **`ClinicalOutput`**; **`schema_version` 3**.
- **`pharma_rd/integrations/openai_clinical.py`**: `call_clinical_gpt_analysis` with JSON-object response format; degrades on connection, timeout, rate limit, API errors.
- **`clinical.py`**: after internal research merge, **`_apply_clinical_gpt`** — no key → skip note; no rows → empty skip; success → structured fields; failure → **`integration_notes`** + **`data_gaps`** (stage completes).
- **API key (operator guidance):** set **`PHARMA_RD_OPENAI_API_KEY`** in **`pharma_rd/.env`** (from **`.env.example`**) or **export** in the shell before **`uv run pharma-rd run`** / scheduler; optional **`PHARMA_RD_OPENAI_MODEL`**, **`PHARMA_RD_OPENAI_TIMEOUT_SECONDS`**, **`PHARMA_RD_INSIGHT_ORG_DISPLAY_NAME`**.
- **README** + **`.env.example`**: document when/where to set the key and degrade-vs-fail policy.
- Tests: **`test_clinical.py`** (mocked GPT, failure path); **`test_config.py`** (OpenAI settings); **`test_artifacts_read_model`** (schema 3 fixture).

### File List

- `pharma_rd/pyproject.toml`
- `pharma_rd/uv.lock`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/integrations/openai_clinical.py`
- `pharma_rd/pharma_rd/agents/clinical.py`
- `pharma_rd/tests/agents/test_clinical.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/tests/persistence/test_artifacts_read_model.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Story 3.3 — OpenAI GPT-4o clinical analyst pass, **`ClinicalOutput` v3**, config + docs + tests; degrade on missing key / API errors.

- 2026-04-05: Code review patches — `internal_research` log before GPT step; guard empty OpenAI `choices`.

### Review Findings

- [x] [Review][Patch] Emit `internal_research` structured log immediately after `_merge_internal_research` (before `_apply_clinical_gpt`) so log order matches semantics [`pharma_rd/pharma_rd/agents/clinical.py`] — fixed 2026-04-05

- [x] [Review][Patch] Guard empty `resp.choices` before indexing in `call_clinical_gpt_analysis` (avoid `IndexError` on odd API responses) [`pharma_rd/pharma_rd/integrations/openai_clinical.py`] — fixed 2026-04-05

- [x] [Review][Defer] Third-party OpenAI/HTTP loggers at DEBUG could surface request bodies in some deployments — verify logging policy and logger levels in staging/production; not introduced by this story alone.

---

**Story completion status:** **done** — code review complete; patch findings applied 2026-04-05.
