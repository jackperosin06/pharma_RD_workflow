# Story 6.5: GPT-powered synthesis

Status: done

## Story

As a **workflow operator**,
I want **Synthesis to use GPT-4o to reason across Clinical, Competitor, and Consumer outputs**,
So that **ranking, rationale, evidence linkage, and urgency reflect strategic judgment** while **structured output remains machine-validated** (FR14–FR17, FR27–FR28).

## Acceptance Criteria

1. **Given** **`ClinicalOutput`**, **`CompetitorOutput`**, and **`ConsumerOutput`** are loaded for a run (FR14)  
   **When** **`PHARMA_RD_OPENAI_API_KEY`** is **set**  
   **Then** the Synthesis stage **does not** use the **legacy deterministic ranking path** for that run; instead it **calls OpenAI** (default **gpt-4o**, configurable) with a **system prompt** positioning the model as a **pharmaceutical strategy advisor**  
   **And** the **user** message includes **serialized structured inputs** (JSON or approved compact format) including **GPT enrichment fields** from stories **3.3**, **4.4**, **5.4** when present  

2. **Given** a model response  
   **When** parsed and validated  
   **Then** the stage produces **`SynthesisOutput`** that **fully conforms** to the existing **`SynthesisOutput`** Pydantic model (FR15–FR17, FR27–FR28): **`ranked_opportunities`**, **`evidence_references`**, **`commercial_viability`**, **`signal_characterization`**, **`scan_summary_lines`**, **`aggregated_upstream_gaps`**, etc.  
   **And** **`ranking_criteria_version`** reflects the GPT-based approach (e.g. `gpt_strategy_v1`)  

3. **Given** the model returns **invalid JSON** or **schema validation fails**  
   **When** the stage runs  
   **Then** the stage **fails** with a **clear operator error** (NFR-R1) **or** a **single bounded retry** with repair prompt—**document** the policy; **no** silent fallback to deterministic logic unless explicitly configured for **practice only**  

4. **Given** **`PHARMA_RD_OPENAI_API_KEY`** is **unset**  
   **When** Synthesis runs  
   **Then** documented behavior: **fail** with message to set key, **or** optional **feature flag** to run **legacy deterministic** synthesis for offline dev—must be **explicit** in README  

5. **Given** **tests**  
   **When** CI runs  
   **Then** OpenAI mocked; golden fixtures produce valid **`SynthesisOutput`**; regression tests ensure **contract** fields required by **7.6** and **Delivery** remain populated  

## Tasks / Subtasks

- [x] Replace or branch **`synthesis.py`** so GPT path is primary when key present; remove **dead deterministic** code paths only after QA sign-off **or** guard behind flag **`PHARMA_RD_SYNTHESIS_MODE=gpt|deterministic`**.  
- [x] Implement **JSON mode** / **structured output** + **Pydantic** parse of model output into **`SynthesisOutput`**; handle token limits (chunking or summarize-then-synthesize—document limits).  
- [x] Update **NFR-P1** / stage timeout settings for longer LLM calls.  
- [x] Comprehensive tests: mock API, schema validation failures, missing key.  
- [x] Architecture / README: **deterministic synthesis deprecated** when GPT mode on.  

### Review Findings

- [x] [Review][Patch] Enforce at most **10** `ranked_opportunities` after GPT parse (system prompt says max 10; Pydantic does not enforce count) — `openai_synthesis.py` (`_parse_partial` / assembly).
- [x] [Review][Patch] Per-list **40-item** cap: `cap_clinical` / `cap_competitor` / `cap_consumer` use **`break` after the first truncated list**, so a second list in the same domain can stay **uncapped** (e.g. both `publication_items` and `internal_research_items` > 40) — `openai_synthesis.py` (~60–103).
- [x] [Review][Defer] Repair prompt concatenates **full** `user_content` again — acceptable MVP cost/latency; optimize later if retries become hot — `openai_synthesis.py` (~186–191) — deferred, pre-existing pattern.

## Dev Agent Record

### Implementation Plan

- Branch on **`PHARMA_RD_SYNTHESIS_MODE`**: **`gpt`** (default) requires **`PHARMA_RD_OPENAI_API_KEY`**; **`deterministic`** keeps legacy **`_run_synthesis_deterministic`** for CI/offline.
- New **`integrations/openai_synthesis.py`**: JSON user payload from upstream models (per-list cap 40), **`response_format` JSON** via existing **`run_chat_json_completion`**, **`RankedOpportunityItem`** + **`signal_characterization`** parse; one repair retry on failure.
- **`aggregated_upstream_gaps`** and **`scan_summary_lines`** remain deterministic from upstream for transparency; **`ranking_criteria_version`** **`gpt_strategy_v1`** for GPT path.
- **`PHARMA_RD_OPENAI_SYNTHESIS_TIMEOUT_SECONDS`** (default 180) for synthesis-only OpenAI client timeout (NFR-P1).

### Completion Notes

- **`pytest`** sets **`PHARMA_RD_SYNTHESIS_MODE=deterministic`** in **`tests/conftest.py`** so CI needs no API key; GPT paths covered with mocked **`run_chat_json_completion`**.
- Full suite **181** tests passing; **ruff** clean.

### File List

- `pharma_rd/pharma_rd/agents/synthesis.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/integrations/openai_client.py`
- `pharma_rd/pharma_rd/integrations/openai_synthesis.py`
- `pharma_rd/tests/conftest.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Story 6.5 — GPT synthesis mode, OpenAI integration, tests, README and env docs.
- 2026-04-06: Code review patches — max 10 GPT ranked rows + multi-list prompt caps; tests added.

## Dev Notes

- **Ordering:** Depends on **3.3**, **4.4**, **5.4** for full value; can stub missing upstream GPT fields.  
- **Risk:** Model hallucination—keep **evidence_references** tied to **upstream IDs** where possible; consider **forcing** model to cite upstream reference strings only.  
- **iNova** / org naming: configurable in prompt.  

## References

- FR14, FR15, FR16, FR17, FR27, FR28, NFR-R1, NFR-P1  
- `pharma_rd/pharma_rd/agents/synthesis.py`, `pharma_rd/pharma_rd/pipeline/contracts.py`  
