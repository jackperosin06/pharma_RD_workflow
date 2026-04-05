# Story 7.4: Human-owned pursuit language in the report

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **compliance-conscious stakeholder**,
I want **clear language that recommendations are not approvals**,
so that **pursuit remains explicitly human-owned** (FR22).

## Acceptance Criteria

1. **Given** any rendered insight report (**`report.md`** and **`report.html`** from Delivery)  
   **When** a recipient reads the **run summary** (executive view) and **each ranked opportunity**  
   **Then** **disclaimer language** states that listed items are **recommendations** (not approvals) and that **pursuit / portfolio decisions remain human-owned**  
   **And** the same intent appears in **both** Markdown and HTML outputs (no HTML-only or MD-only disclaimer).

2. **Given** the report layout  
   **When** a recipient scans the document  
   **Then** the disclaimer is **visible** in more than one place — e.g. a **short callout in or near the run summary**, **per-opportunity reminder** (or clearly grouped wording under each opportunity), and a **governance block** (existing `## Governance and disclaimer` section)  
   **And** the HTML report includes a **`<footer>`** (or equivalent semantic footer region before `</body>`) repeating the core human-judgment message so it is not “governance-only buried at the end” as the only surface.

3. **Given** CI  
   **When** tests run  
   **Then** assertions **pin** required **keywords or phrases** (e.g. **recommendation(s)** and **human** + **pursuit** / **decision** in a sensible phrase) in **both** rendered artifacts for a fixture run — without coupling tests to a full legal paragraph if copy is iterated later (prefer **substring** checks on stable terms aligned to FR22).

## Tasks / Subtasks

- [x] **Copy & constants** — `pharma_rd/pharma_rd/agents/delivery.py` (or `pharma_rd/pharma_rd/agents/delivery_disclaimer.py` if you split for clarity):
  - [x] Replace **`_DISCLAIMER`** placeholder (and the “Story 7.4 will refine” parenthetical) with **final practice-build** strings that satisfy FR22 and AC1–2. Split into **short executive one-liner**, **per-opportunity line** (repeated or templated), and **full governance paragraph** as needed.
  - [x] Keep tone **clear and non-claims** — no regulatory sign-off language; align with PRD FR22 [Source: `_bmad-output/planning-artifacts/prd.md`].

- [x] **`_render_markdown`** — Insert:
  - [x] **Executive / run summary:** visible disclaimer (e.g. blockquote `>` or bold lead paragraph immediately under `# Insight report` or at top of `## Run summary`) — must be readable in plain text.
  - [x] **Each ranked opportunity:** one line (e.g. blockquote or italic) after the opportunity heading block (after title / before or after rationale) stating **not an approval** / **human-owned pursuit** intent.
  - [x] **`## Governance and disclaimer`:** retain section; populate with **full** disclaimer text (can combine with executive copy if duplication is too high — but AC2 requires **summary + not buried-only**, so at least **two** distinct surfaces: summary-adjacent + governance, plus per-opportunity).

- [x] **`_render_html`** — Mirror Markdown intent:
  - [x] Run summary: same executive disclaimer in semantic HTML (`<aside>`, `<p class="...">`, or `<blockquote>` — avoid relying on external CSS files; inline/minimal style OK).
  - [x] Each opportunity: matching per-opportunity line.
  - [x] Governance `<h2>` section + **`<footer>...</footer>`** before `</body>` with the core FR22 message (may shorten to one sentence if full text is in governance section).

- [x] **Readability helper** — `pharma_rd/pharma_rd/readability/insight_report.py`:
  - [x] If section headings change, update **`_MARKDOWN_SECTION_MARKERS`** in the **same** change set; if headings stay the same, extend **`validate_readable_insight_report`** with optional **`required_fr22_snippets: Sequence[str] | None`** or document that **delivery tests** assert FR22 phrases (pick one approach; avoid duplicating the entire legal paragraph in the helper).

- [x] **Tests** — `pharma_rd/tests/agents/test_delivery.py` (and readability tests if extended):
  - [x] Assert **Markdown** contains agreed substrings in **run summary area**, **at least one opportunity block**, and **governance** section.
  - [x] Assert **HTML** contains the same intent (escaped text in HTML — search **decoded** file text or stable English substrings that survive `escape()`).
  - [x] **Regression:** existing report size / distribution tests still pass; **`validate_readable_insight_report`** still passes on canonical **`report.md`**.

- [x] **README** — `pharma_rd/README.md`: short bullet under Delivery / recipients that reports carry **FR22** human-judgment disclaimers (where to look: summary, each opportunity, governance, HTML footer).

- [x] **Optional note for product/legal:** If your org needs **exact** approved wording, add a one-line README pointer that **copy is configurable** only if you introduce constants — otherwise document that strings live in **`delivery.py`** for a single edit point.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR22** | Recommendations vs approvals; **human-owned** pursuit decisions [Source: `_bmad-output/planning-artifacts/prd.md`]. |
| **Epic 7.4** | Visibility in **executive** + **each opportunity** + not **buried-only** [Source: `_bmad-output/planning-artifacts/epics.md`]. |

### Architecture compliance

- **Delivery** does not re-rank synthesis; only **presentation** strings change [Source: `_bmad-output/planning-artifacts/architecture.md` — Delivery boundary].
- **No new dependencies**; stdlib **`html.escape`** already used for HTML.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Delivery | `pharma_rd/pharma_rd/agents/delivery.py` |
| Readability | `pharma_rd/pharma_rd/readability/insight_report.py` (optional API tweak) |
| Tests | `pharma_rd/tests/agents/test_delivery.py`, `pharma_rd/tests/readability/test_insight_report.py` |
| Docs | `pharma_rd/README.md` |

### Previous story intelligence (7.3)

- **`report.md`** / **`report.html`** both emitted; file-drop copies both; **`validate_readable_insight_report`** checks **`## Run summary`**, **`## Ranked opportunities`**, **`## Governance and disclaimer`** — coordinate any heading edits.
- Placeholder **`_DISCLAIMER`** explicitly deferred FR22 to **7.4** — replace wholesale.

### Technical requirements (guardrails)

- **Python 3.12**; **Ruff** 88; deterministic tests (**tmp_path**).
- **Pydantic `DeliveryOutput`:** no schema bump required unless you add metadata fields (prefer **not** for copy-only story).

### Git intelligence

- Touch **`delivery.py`** only as needed; keep **`distribute_insight_report`** unaware of disclaimer content.

### Latest tech / deps

- None.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

—

### Completion Notes List

- **Code review (2026-04-06):** Clean review — no patch or decision-needed findings; optional note: keep **`_FR22_*_PLAIN`** and **`_FR22_*_MD`** pairs aligned when editing copy.
- FR22 strings centralized at top of **`delivery.py`** (`*_PLAIN` / `*_MD`); executive blockquote after **`## Run summary`**, per-opportunity blockquote after each **`###`**, governance paragraph; HTML uses **`<blockquote>`**, per-opportunity **`<em>`**, **`<footer>`** before **`</body>`**.
- **`validate_readable_insight_report`** unchanged (headings stable); FR22 covered in **`test_delivery`** substrings.
- README Delivery + For recipients updated for FR22 and single edit point (**`delivery.py`**).

### File List

- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/tests/agents/test_delivery.py`
- `pharma_rd/README.md`

### Change Log

- 2026-04-06: Story 7.4 — FR22 disclaimers in MD/HTML, tests, README.
- 2026-04-06: Code review passed; story marked **done**.

## References

- Epic 7 / Story 7.4: `_bmad-output/planning-artifacts/epics.md`
- PRD FR22: `_bmad-output/planning-artifacts/prd.md`
- Prior: `_bmad-output/implementation-artifacts/7-3-recipients-open-and-read-the-report.md`, `7-1-render-structured-insight-report-artifact.md`

---

**Story completion status:** done — Code review complete; **`uv run ruff check`** and **`uv run pytest`** passing (125 tests).
