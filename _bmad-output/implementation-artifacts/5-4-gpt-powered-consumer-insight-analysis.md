# Story 5.4: GPT-powered consumer insight analysis

Status: done

## Story

As a **workflow operator**,
I want **the Consumer stage to send collected market signals to GPT-4o for market-analyst interpretation**,
So that **outputs surface unmet needs, demand patterns, and consumer signals relevant to line-extension opportunities** (extends FR11–FR13).

## Acceptance Criteria

1. **Given** the Consumer agent has **aggregated** feedback themes, pharmacy sales trends, and unmet-need/demand signals (existing FR11–FR13 path)  
   **When** **`PHARMA_RD_OPENAI_API_KEY`** is **set**  
   **Then** the stage **calls OpenAI** (default **gpt-4o**, configurable) with a **system prompt** positioning the model as a **pharmaceutical market analyst**  
   **And** the **user** message includes **structured** consumer payload (themes, trends, demand signals—**non-PHI** practice assumption per NFR-S4).  

2. **Given** a successful model response  
   **When** merged into **`ConsumerOutput`**  
   **Then** structured output includes **GPT-derived insight** (e.g. unmet need synthesis, demand pattern summary, **line-extension relevance**) in validated fields; **schema_version** updated if needed  
   **And** upstream **raw signal rows** remain available for audit.  

3. **Given** OpenAI **failure** or **missing key**  
   **When** the stage completes  
   **Then** same **degradation / fail-fast policy** as **3.3** and **4.4** (documented centrally).  

4. **Given** **tests**  
   **When** CI runs  
   **Then** mocks only; assertions on prompt shape and merged output; no secrets in logs.  

## Tasks / Subtasks

- [x] Extend **`consumer.py`** with post-aggregation GPT call; shared OpenAI helper from 3.3.  
- [x] Extend **`ConsumerOutput`** for analyst fields.  
- [x] Tests: mock OpenAI; empty-consumer path still **NFR-I1** compliant.  
- [x] README note: **practice** data must stay **non-PHI** in prompts unless enterprise privacy design exists.  

## Dev Notes

- If **mock/practice** consumer data is used, prompts should **state** that explicitly to reduce overconfidence.  
- Coordinate field names with **6.5** input expectations.  

## References

- FR11, FR12, FR13, NFR-I1, NFR-S4  
- `pharma_rd/pharma_rd/agents/consumer.py`, `pharma_rd/pharma_rd/pipeline/contracts.py`  

## Dev Agent Record

### Agent Model Used

Cursor (implementation agent)

### Debug Log References

### Completion Notes List

- **Closure (2026-04-05):** Story marked **done** after code review; defer items remain tracked for optional follow-up.

- **`ConsumerGptAnalysis`** + optional **`consumer_gpt_analysis`** on **`ConsumerOutput`**; **`schema_version` 5**.
- **`openai_consumer.py`**: `call_consumer_gpt_analysis`; system prompt distinguishes **practice** vs non-practice (`practice_mode`); JSON fields **`unmet_need_synthesis`**, **`demand_pattern_summary`**, **`line_extension_relevance`**.
- **`consumer.py`**: build **`ConsumerOutput`**, structured logs (`consumer_feedback`, `consumer_pharmacy_sales`, `consumer_unmet_need_demand`), then **`_apply_consumer_gpt`** (same degrade policy as 3.3 / 4.4).
- Tests: **`test_consumer.py`** (mocked GPT, failure path); **`test_synthesis.py`** **`upstream_consumer_schema_version`** **5**.
- README + `.env.example`: GPT consumer + NFR-S4 practice/non-PHI note.

### File List

- `pharma_rd/pharma_rd/integrations/openai_consumer.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/agents/consumer.py`
- `pharma_rd/tests/agents/test_consumer.py`
- `pharma_rd/tests/agents/test_synthesis.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-05: Story 5.4 — consumer GPT integration, **`ConsumerOutput` v5**, tests, docs.

- 2026-04-05: Code review complete — story accepted **done** (defer items logged).

### Review Findings

- [x] [Review][Defer] Optional test hardening for **AC4** — assert `call_consumer_gpt_analysis` receives a **`ConsumerOutput`** with expected non-empty lists when appropriate, or snapshot key fields in **`_payload_for_prompt`** (current tests mock the integration and assert merge behavior).

- [x] [Review][Defer] **Large consumer GPT payloads** — no explicit token/context cap before OpenAI; same follow-up theme as clinical/competitor GPT stories if operators attach very large fixtures.

---

**Story completion status:** **done** — code review complete 2026-04-05; defer items tracked for optional follow-up.
