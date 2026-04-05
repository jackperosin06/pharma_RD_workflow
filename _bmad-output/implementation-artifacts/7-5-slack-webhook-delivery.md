# Story 7.5: Slack webhook delivery

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator** or **report recipient**,
I want **a concise Slack notification when an insight run completes**,
so that **R&D and marketing see signal context and where to open the full report without polling the pipeline** (extends FR19 / delivery surface; complements file-drop and on-disk HTML).

## Acceptance Criteria

1. **Given** **`PHARMA_RD_SLACK_WEBHOOK_URL`** is **set** in the environment (non-empty, trimmed)  
   **When** the Delivery stage finishes writing **`report.md`** and **`report.html`** to the artifact root (HTML must already exist on disk)  
   **Then** the Delivery flow **POST**s to that URL with a **Slack Block Kit** payload (`blocks` array per Slack API) — **not** a plain-text wall — using **sections**, **dividers** (`divider` blocks), and **`mrkdwn` / `header` / `section`** text with **bold** where appropriate so the message looks **clean and professional**.

2. **Given** **`PHARMA_RD_SLACK_WEBHOOK_URL`** is **unset** or **empty**  
   **When** Delivery runs  
   **Then** **no** HTTP request is made to Slack, the stage **does not crash**, **`distribution_channel`** / existing file-drop behavior is **unchanged**, and a **structured log** line records that Slack is **not configured** (e.g. event like `slack_notify_skipped`, outcome `skipped`, **INFO** level — **not** ERROR).

3. **Given** the webhook is configured  
   **When** the message is built  
   **Then** it includes **all** of the following blocks/sections (exact Block Kit layout is an implementation detail, but **content** must be present):
   - **Header:** **Run date** (use **UTC** calendar date for the delivery execution unless the story implementation reads **`runs.created_at`** from the DB — pick one approach and document it) **and** **pharma_RD** branding so recipients immediately recognize the product (e.g. title text like **“pharma_RD insight report”**).
   - **Executive summary:** Short copy describing **`signal_characterization`** from **`SynthesisOutput`** in plain language (e.g. **quiet** vs **net_new** / **mixed** / **unknown** — “high-signal week” vs “quiet week” style phrasing).
   - **Top 3 ranked opportunities:** From **`ranked_opportunities`**, take the **top 3 by `rank`** (sorted ascending). For **each**: **title**, **one-sentence rationale** (derive from **`rationale_short`** — truncate at word/sentence boundary with ellipsis if needed; cap length for Slack limits), and a **commercial viability indicator** (MVP: **short excerpt** from **`commercial_viability`** or a **single-line** summary — document the rule; avoid huge blobs).
   - **Scan / monitoring summary:** A line (or short list) stating which **therapeutic areas** and **competitor watchlists** were monitored — use **`get_settings()`** → **`Settings.therapeutic_area_labels()`** and **`Settings.competitor_labels()`** so it reflects **configuration**; if empty, say **not configured** / **none** explicitly (honest practice mode).
   - **FR22 disclaimer:** Text stating items are **recommendations**, **not approvals**, and **pursuit decisions are human-owned** (reuse or mirror tone from `pharma_rd.agents.delivery` FR22 strings — do not invent contradictory legal meaning).
   - **Closing / report location:** A line that the **full HTML report** is available, showing the **on-disk path** for MVP: **absolute or resolved** path to **`{artifact_root}/{run_id}/delivery/report.html`** (or the path string operators care about). **Design:** build this line via a **single helper** e.g. `format_report_location_for_notification(artifact_root, run_id, *, base_url: str | None = None)` so **MVP** passes **`base_url=None`** and prints the filesystem path; a **future** production deployment can pass **`base_url="https://..."`** and emit a **URL** without rewriting Block Kit assembly (swap implementation inside the helper only).

4. **Given** the Slack API returns **4xx/5xx** or the request **times out**  
   **When** Delivery handles the failure  
   **Then** the pipeline **does not crash** the whole run (align with existing **distribution** behavior: log **`slack_notify_failed`** or similar with **actionable** detail, **no secrets** in logs). **`DeliveryOutput`** (or structured logs only — prefer **additive** `DeliveryOutput` fields for operator visibility) should record **slack status** separately from **file_drop** distribution.

5. **Given** CI  
   **When** tests run  
   **Then** **fully mocked** HTTP: when the webhook URL is set, assert **`httpx` POST** (or the project’s HTTP client) is invoked with a **JSON body** containing **`blocks`** and **expected substrings** (titles, signal label, FR22 keywords). When the URL is unset, assert **no outbound POST** and assert the **skip** log event (e.g. `caplog` / structured log test pattern used elsewhere).

## Tasks / Subtasks

- [x] **Configuration** — `pharma_rd/pharma_rd/config.py` + **`pharma_rd/.env.example`**:
  - [x] Add **`slack_webhook_url: str | None`** (or `str` default `""` with validator → `None`) with env **`PHARMA_RD_SLACK_WEBHOOK_URL`**; **never** log the full URL if it contains secrets (prefer log **“configured”** boolean only or truncated host).

- [x] **Slack Block Kit builder** — new module e.g. **`pharma_rd/pharma_rd/integrations/slack_insight_notification.py`** (or under `integrations/`):
  - [x] Pure function(s) to build **`blocks`** list from **`run_id`**, **`SynthesisOutput`**, **`Settings`**, **`artifact_root: Path`**, and **report relative path** / resolved absolute path for the HTML file.
  - [x] Respect Slack **text length** limits — truncate long fields with `…` and document caps.
  - [x] **`format_report_location_for_notification(...)`** as specified in AC3 (path vs future URL).

- [x] **HTTP POST** — Use existing **`httpx`** client patterns from the repo (timeouts from **`PHARMA_RD_HTTP_*`** or dedicated shorter timeout for Slack, e.g. **10s** — document). POST JSON **`{"blocks": [...]}`** to the webhook URL (Slack incoming webhooks expect JSON with `text` fallback optional — include **`text`** fallback plain string for notifications clients that ignore blocks, if low cost).

- [x] **Wire into Delivery** — `pharma_rd/pharma_rd/agents/delivery.py`:
  - [x] After **`report.html`** is written and **before or after** `distribute_insight_report` — **after** HTML exists on disk (required by AC). Order: **md → html → slack (if configured) → existing distribution**.
  - [x] Avoid circular imports: follow **`report_distribution.py`** pattern (integrations module must not import `pipeline.contracts` if that creates cycles — pass primitives or use **`TYPE_CHECKING`**).

- [x] **`DeliveryOutput`** — `pharma_rd/pharma_rd/pipeline/contracts.py`:
  - [x] Add **additive** optional fields, e.g. **`slack_notify_status`**: **`Literal["ok", "skipped", "failed"]`** and optional **`slack_notify_detail`**: **`str`** (short, safe), **or** document **log-only** if schema bump is undesirable — **prefer additive** with defaults so legacy JSON still loads.

- [x] **Logging** — `pharma_rd/pharma_rd/logging_setup.py`: allowlist new structured keys (e.g. **`slack_notify_status`**, **`event`** = `slack_notify_skipped` | `slack_notify_complete` | `slack_notify_failed`).

- [x] **Tests** — **`pharma_rd/tests/integrations/test_slack_insight_notification.py`** (or **`tests/agents/test_delivery.py`**):
  - [x] Mock **`httpx.Client.post`** or **`httpx.post`** (match project pattern); assert **blocks** payload contains required substrings.
  - [x] **URL unset:** no POST; **`slack_notify_skipped`** (or equivalent) in logs; **`DeliveryOutput`** reflects skipped.
  - [x] **`tests/pipeline/test_contracts.py`**: round-trip **`DeliveryOutput`** with new fields defaulted for old JSON.

- [x] **README** — Document **`PHARMA_RD_SLACK_WEBHOOK_URL`**, behavior when unset, and that Block Kit is used; note MVP shows **filesystem path** in Slack.

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR19** (open channel) | Slack as an additional **delivery surface**; orthogonal to **`distribution_channel`**. |
| **FR22** | Disclaimer text must align with Delivery report language. |
| **NFR-R1** | Actionable errors on Slack failure; no silent drop without log. |
| **NFR-S1** | Webhook URL is a **secret** — env only; not in repo. |

### Architecture compliance

- **Outbound I/O** in **`integrations/*`**; Delivery stays orchestration-only [Source: `_bmad-output/planning-artifacts/architecture.md`].
- **Block Kit:** [Slack Block Kit reference](https://api.slack.com/block-kit) — use **`header`**, **`section`**, **`divider`**, **`context`** as needed.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Config | `pharma_rd/pharma_rd/config.py`, `pharma_rd/.env.example` |
| Slack | `pharma_rd/pharma_rd/integrations/slack_insight_notification.py` (name flexible) |
| Delivery | `pharma_rd/pharma_rd/agents/delivery.py` |
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` |
| Tests | `pharma_rd/tests/integrations/…`, `pharma_rd/tests/agents/test_delivery.py`, `pharma_rd/tests/pipeline/test_contracts.py` |
| Docs | `pharma_rd/README.md` |

### Previous story intelligence (7.4 / 7.2)

- **`SynthesisOutput`**: **`signal_characterization`**, **`scan_summary_lines`**, **`ranked_opportunities`** with **`rank`**, **`title`**, **`rationale_short`**, **`commercial_viability`**.
- **Settings**: **`therapeutic_area_labels()`**, **`competitor_labels()`** — use for “what was monitored.”
- **`run_delivery`** already writes **`report.html`** then calls **`distribute_insight_report`** — insert Slack **after** HTML write.

### Technical requirements (guardrails)

- **Python 3.12**; **Ruff** 88; **httpx** already in project.
- **Deterministic tests** — no real network; **mock** HTTP.

### Project structure notes

- Package **`pharma_rd.pharma_rd`**; follow **`integrations/report_distribution.py`** logging style.

### Git intelligence

- Mirror **`httpx`** usage from clinical/competitor connectors where applicable.

### Latest tech / deps

- No new dependencies if **`httpx`** suffices.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

_(none)_

### Completion Notes List

- Implemented **`PHARMA_RD_SLACK_WEBHOOK_URL`** / **`PHARMA_RD_SLACK_WEBHOOK_TIMEOUT_SECONDS`** (default **10s**) in `settings`; logs only **`slack_webhook_configured`** and **`slack_webhook_host`** (never full URL).
- **Run date:** UTC **calendar date** at delivery execution via **`datetime.now(UTC).date()`** (documented here; not DB `runs.created_at`).
- **`slack_insight_notification.py`:** Block Kit **`header`**, **`divider`**, **`section`** (mrkdwn), plain **`text`** fallback; **`TYPE_CHECKING`** imports for contracts to avoid circular import with **`pipeline` package**.
- **`format_report_location_for_notification`:** MVP resolves absolute **`report.html`** path; optional **`base_url`** for future HTTPS links.
- Truncation: rationale **220** chars, commercial **140** chars (word-bounded ellipsis).
- Delivery order: **md → html → Slack (if configured) → `distribute_insight_report`**.
- **`DeliveryOutput`:** **`slack_notify_status`** / **`slack_notify_detail`** (additive defaults for legacy JSON).
- Tests: **`httpx.Client`** mocked; **`ruff`** + full **`pytest`** green (**132** tests).

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/pharma_rd/integrations/slack_insight_notification.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/.env.example`
- `pharma_rd/README.md`
- `pharma_rd/tests/integrations/test_slack_insight_notification.py`
- `pharma_rd/tests/agents/test_delivery.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/7-5-slack-webhook-delivery.md`

### Change Log

- **2026-04-05:** Story 7.5 implemented — Slack Block Kit webhook, config, delivery wiring, `DeliveryOutput` fields, tests, README.

### Review Findings

- [x] [Review][Patch] Sanitize or escape Slack `mrkdwn` for user-derived strings (`title`, `rationale_short`, `commercial_viability`) in Block Kit sections so `*`, `_`, and backticks cannot break or spoof formatting — `pharma_rd/pharma_rd/integrations/slack_insight_notification.py` (opportunity loop; consider Slack’s escaping rules or `plain_text` where appropriate). **Resolved:** `_escape_slack_mrkdwn_user_text()` applied to user/config strings and path; tests added.

- [x] [Review][Patch] Use a stable sort for top opportunities: `sorted(..., key=lambda r: (r.rank, r.title))` before `[:3]` so tied ranks are deterministic — `pharma_rd/pharma_rd/integrations/slack_insight_notification.py` (~139). **Resolved:** stable `(rank, title)` sort; test added.

- [x] [Review][Defer] `config.py` working-tree diff includes many settings unrelated to Slack (consumer/pharmacy/unmet/distribution, etc.) — pre-existing mixed scope on branch, not introduced solely by story 7-5 — deferred, pre-existing

## References

- Slack incoming webhooks: [Slack API — incoming webhooks](https://api.slack.com/messaging/webhooks)
- Block Kit: [Block Kit](https://api.slack.com/block-kit)
- Prior: `7-4-human-owned-pursuit-language-in-the-report.md`, `7-2-distribute-report-to-r-d-and-marketing-recipients.md`
- Contracts: `pharma_rd/pharma_rd/pipeline/contracts.py` — `SynthesisOutput`, `RankedOpportunityItem`

---

**Story completion status:** done — code review patches applied (2026-04-05)
