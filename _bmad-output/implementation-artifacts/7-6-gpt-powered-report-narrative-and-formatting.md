# Story 7.6: GPT-powered report narrative and formatting

Status: done

## Story

As a **workflow operator**,
I want **Delivery to generate the executive insight report via GPT-4o as narrative HTML**,
So that **recipients receive a CEO-ready document**: prose executive summary, contextual narratives per opportunity, commercial conclusion, **FR22** disclaimer, and **high-quality readable styling** for browser and Slack surfaces (extends FR18, FR22; aligns with NFR-P2).

## Acceptance Criteria

1. **Given** **`SynthesisOutput`** exists for **`run_id`**  
   **When** **`PHARMA_RD_OPENAI_API_KEY`** is **set** **and** **`PHARMA_RD_REPORT_RENDERER`** is **`gpt`** (the key alone does **not** enable the narrative GPT path; default renderer **`template`** keeps CI and local runs deterministic without GPT)  
   **Then** Delivery **calls OpenAI** (default **gpt-4o**, configurable) with a **system prompt** positioning the model as a **senior pharmaceutical strategy consultant**  
   **And** the **user** message includes **full synthesis payload** (and key **settings** context: TA scope, competitor watchlist **labels**—no secrets) sufficient to produce the report  

2. **Given** a successful model response  
   **When** artifacts are written  
   **Then** **`report.html`** is **valid, self-contained HTML** (embedded or linked **CSS**) suitable for **direct browser open** and **Slack** unfurl-friendly preview where applicable  
   **And** the document includes:  
   - **Executive summary** as **continuous prose** (not bullet-only).  
   - **Narrative context** for **each ranked opportunity** (not template stubs only).  
   - **Commercially framed conclusion** section.  
   - **FR22** disclaimer **prominently** (executive + per-opportunity and/or footer as required by compliance story **7.4**).  

3. **Given** **`report.md`** is still required for distribution / audit  
   **When** Delivery runs  
   **Then** either **GPT also emits Markdown** in one call, **or** a **second** constrained call / deterministic MD-from-HTML—**document** approach; file-drop and **Slack** integrations (**7.2**, **7.5**) **continue to work**  

4. **Given** OpenAI **failure**  
   **When** Delivery runs  
   **Then** **fail** with actionable error **or** **fallback** to pre-7.6 template renderer—**document**; no empty **`report.html`** without explanation (NFR-R1)  

5. **Given** **security**  
   **When** HTML is produced  
   **Then** output is **safe for local `file://` viewing**: avoid **inline scripts** from model unless sanitized; if model returns untrusted HTML, **sanitize** (allowlist tags) before write (document library choice)  

6. **Given** **tests**  
   **When** CI runs  
   **Then** OpenAI mocked; **assertions on key HTML fragments** (required strings, structure, sanitization behavior); **no API key** in repo  

## Tasks / Subtasks

- [x] Refactor **`delivery.py`**: GPT path generates **`report.html`** (and **`report.md`** per AC3); retire or flag **string-template** path as **`PHARMA_RD_REPORT_RENDERER=gpt|template`**.  
- [x] Add **HTML sanitization** step if model returns raw HTML.  
- [x] Tune **Slack** integration (**7.5**) to excerpt **GPT prose** within Block Kit limits or attach summary.  
- [x] Tests: mocks, sanitization, FR22 string presence, fallback path.  
- [x] **README**: CEO-ready positioning; token/latency expectations (NFR-P1).  

## Dev Notes

- **Depends on:** **6.5** for GPT-quality **`SynthesisOutput`**; may accept deterministic synthesis if flag allows.  
- **Report GPT gate:** operators need **`PHARMA_RD_REPORT_RENDERER=gpt`** **and** **`PHARMA_RD_OPENAI_API_KEY`** for the narrative report path; **`template`** remains the default for CI and environments that should not call OpenAI for delivery.  
- **AC2 (MVP):** layout and per-section content are primarily **model + system prompt**, with **executive FR22** reinforced in code via `_ensure_fr22_html_fragment`; a future story may add structural HTML validation.  
- **Slack:** Block Kit **3000-char** limits may require **truncation** of GPT narrative with “open full HTML” link/path.  
- **Brand:** “pharma_RD” / iNova naming—use **settings** or constants for white-label.  
- **Review (2026-04-05):** change set may include related **Epic 8** config and **sprint-status** updates in one integration drop—accepted as a single bundle.  

## References

- FR18, FR19, FR20, FR21, FR22, NFR-P2, NFR-R1, NFR-S1  
- `pharma_rd/pharma_rd/agents/delivery.py`, `pharma_rd/pharma_rd/integrations/slack_insight_notification.py`  

## Dev Agent Record

### Implementation Plan

- **`PHARMA_RD_REPORT_RENDERER`**: `gpt` | `template` (default **template** for CI).
- **`openai_report_delivery.py`**: one JSON completion (`report_html` fragment, `report_markdown`, optional `slack_executive_excerpt`).
- **`report_html_sanitize.py`**: **`nh3.clean()`** on body fragment; trusted shell in **`delivery._wrap_gpt_html_fragment`**.
- FR22 injection if model omits phrases; fallback to template when **`report_gpt_fallback_on_error`** (default true).
- Slack: **`gpt_executive_excerpt`** replaces signal-only executive block when set.

### Completion Notes

- **187** tests passing; **`nh3`** dependency added.
- **`tests/conftest.py`** defaults **`PHARMA_RD_REPORT_RENDERER=template`**.

### File List

- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/integrations/openai_client.py`
- `pharma_rd/pharma_rd/integrations/openai_report_delivery.py`
- `pharma_rd/pharma_rd/integrations/report_html_sanitize.py`
- `pharma_rd/pharma_rd/integrations/slack_insight_notification.py`
- `pharma_rd/pyproject.toml`
- `pharma_rd/uv.lock`
- `pharma_rd/tests/conftest.py`
- `pharma_rd/tests/agents/test_delivery.py`
- `pharma_rd/tests/integrations/test_report_html_sanitize.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-06: Story 7.6 — GPT report renderer, nh3 sanitization, Slack excerpt, tests, README.

### Review Findings

#### Resolved decisions (2026-04-05)

- [x] [Review][Decision] **AC1 vs `PHARMA_RD_REPORT_RENDERER`** — **Resolved 1C (hybrid):** AC1, Dev Notes, and README describe **both** `PHARMA_RD_REPORT_RENDERER=gpt` **and** `PHARMA_RD_OPENAI_API_KEY`; default **`template`** for CI/local without GPT narrative.
- [x] [Review][Decision] **AC2 assurance vs prompt-only path** — **Resolved 2A (MVP):** accept prompt-led delivery + `_ensure_fr22_html_fragment`; optional follow-up for structural validation.
- [x] [Review][Decision] **AC6 “snapshot” vs current tests** — **Resolved 3A:** AC6 updated to **assertions on key HTML fragments** (not golden/snapshot files).
- [x] [Review][Decision] **Change-set scope** — **Resolved 4A:** single integration bundle (including related Epic 8 / sprint-status) accepted.

#### Open patches (addressed 2026-04-05)

- [x] [Review][Patch] **Braces in org display name break system prompt** [`openai_report_delivery.py`] — Use `_SYSTEM_PROMPT.replace("{org}", settings.insight_org_display_name)` instead of `str.format`.
- [x] [Review][Patch] **`run_id` can escape artifact root in Slack path** [`slack_insight_notification.py`] — Reject `..` / absolute `run_id`; validate `resolved.relative_to(artifact_root)`; return **relative** `run_id/delivery/report.html` for display.
- [x] [Review][Patch] **Slack webhook `follow_redirects=True`** — `httpx.Client(..., follow_redirects=False)`.
- [x] [Review][Patch] **OpenAI choice may have no message** [`openai_client.py`] — Guard `message is None` and empty `content` before returning.
- [x] [Review][Patch] **Unescaped titles in Markdown report** [`delivery.py`] — `_md_heading_title()` for ranked-opportunity `###` lines.
- [x] [Review][Patch] **HTML sanitization policy** [`report_html_sanitize.py`] — Explicit `url_schemes` for `nh3.clean` + comment.
- [x] [Review][Patch] **Sanitization test coverage** — Tests for `javascript:` href, `onclick`, `iframe`.
- [x] [Review][Patch] **Thin GPT output** [`openai_report_delivery.py`] — Require non-empty HTML and Markdown; reject combined visible text under 40 chars (`thin_gpt_report` → delivery fallback).
- [x] [Review][Patch] **`openai` dependency range** — `openai>=1.59.0,<3` in `pyproject.toml`; `uv.lock` refreshed.
- [x] [Review][Patch] **Slack path leak** — Relative path string in notifications (see above).
- [x] [Review][Patch] **README vs runtime** — README clarifies dual gate (`gpt` + key), thin-output fallback, relative Slack path, `follow_redirects=false`.
