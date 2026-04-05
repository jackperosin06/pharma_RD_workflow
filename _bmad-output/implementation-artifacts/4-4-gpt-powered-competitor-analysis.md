# Story 4.4: GPT-powered competitor analysis

Status: done

## Story

As a **workflow operator**,
I want **the Competitor stage to send FDA/regulatory fetch results to GPT-4o for competitive intelligence interpretation**,
So that **outputs highlight strategic significance, threats and opportunities, and anything needing urgent attention** (extends FR8–FR10).

## Acceptance Criteria

1. **Given** the Competitor agent has **completed** ingestion of approvals, disclosures, pipeline items, and patent flags (existing FR8–FR10 path)  
   **When** **`PHARMA_RD_OPENAI_API_KEY`** is **set**  
   **Then** the stage **calls OpenAI** (default **gpt-4o**, configurable) with a **system prompt** positioning the model as a **pharmaceutical competitive intelligence analyst** and including **configured competitor watchlist** context  
   **And** the **user** message contains a **structured summary** of fetched regulatory/competitor payload (no API secrets).  

2. **Given** a successful model response  
   **When** merged into **`CompetitorOutput`**  
   **Then** structured output includes **GPT-derived analysis** (e.g. strategic commentary, threat/opportunity themes, **urgent attention** flags) in **Pydantic-validated** fields with **schema versioning** as needed  
   **And** raw **fetched rows** remain **traceable** in the artifact.  

3. **Given** OpenAI **failure** or **missing key**  
   **When** the stage finishes  
   **Then** documented **degradation or fail-fast** behavior matches the policy chosen in **Story 3.3** (consistency across GPT stories).  

4. **Given** **tests**  
   **When** CI runs  
   **Then** OpenAI is **mocked**; no key required; logs do not emit **secrets** or full MNPI payloads inappropriately (NFR-S1).  

## Tasks / Subtasks

- [x] Reuse shared OpenAI client/settings from 3.3 (extract **`integrations/openai_client.py`** or equivalent if not already shared).  
- [x] Extend **`competitor.py`** post-fetch GPT step; prompts reference **watch scopes** and **observation window**.  
- [x] Extend **`CompetitorOutput`** for analyst fields; version bump if needed.  
- [x] Tests with mocks + fixture JSON.  
- [x] README / `.env.example` cross-links to clinical GPT story for key usage.  

## Dev Notes

- Align **urgent attention** representation with downstream **6.5** (e.g. boolean or severity enum consumable by synthesis).  
- **TLS** for OpenAI already via HTTPS (NFR-S3).  

## References

- FR8, FR9, FR10, NFR-I2, NFR-R1, NFR-S1  
- `pharma_rd/pharma_rd/agents/competitor.py`, `pharma_rd/pharma_rd/pipeline/contracts.py`  

## Dev Agent Record

### Agent Model Used

Cursor (implementation agent)

### Debug Log References

### Completion Notes List

- **Closure (2026-04-05):** Story marked **done** after code review; **`epic-4`** set to **done** in sprint tracking (all Epic 4 stories complete).

- **`openai_client.py`**: `create_openai_client`, `run_chat_json_completion`; refactored **`openai_clinical.py`** to use it.
- **`CompetitorGptAnalysis`** + optional **`competitor_gpt_analysis`** on **`CompetitorOutput`**; **`schema_version` 5**; **`UrgentAttentionSeverity`** for synthesis-friendly **`urgent_attention_severity`**.
- **`openai_competitor.py`**: `call_competitor_gpt_analysis` with JSON-object response; system prompt includes watchlist, pipeline scopes, observation window; user payload has structured approval/disclosure/pipeline/patent rows.
- **`competitor.py`**: **`_apply_competitor_gpt`** after fetch merge — same degrade policy as clinical (story 3.3).
- Tests: **`test_competitor.py`** (mocked GPT, failure path); **`test_synthesis.py`** **`upstream_competitor_schema_version`** **5**.
- README + `.env.example`: cross-link OpenAI env vars for competitor GPT.

### File List

- `pharma_rd/pharma_rd/integrations/openai_client.py`
- `pharma_rd/pharma_rd/integrations/openai_clinical.py`
- `pharma_rd/pharma_rd/integrations/openai_competitor.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/competitor.py`
- `pharma_rd/tests/agents/test_competitor.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Story 4.4 — shared OpenAI helpers, competitor GPT integration, **`CompetitorOutput` v5**, tests, docs.

- 2026-04-05: Code review complete — defer items logged; story accepted **done**.

### Review Findings

- [x] [Review][Defer] Optional normalization if **`urgent_attention_flag`** and **`urgent_attention_severity`** disagree — consider when **6.5** consumes competitor GPT fields.

- [x] [Review][Defer] No explicit bound on competitor GPT user JSON size vs model context window — shared hardening with other GPT stories if operators attach very large fixtures.

---

**Story completion status:** **done** — code review complete 2026-04-05; defer items tracked for follow-up.
