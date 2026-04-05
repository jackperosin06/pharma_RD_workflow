# Story 7.2: Distribute report to R&D and marketing recipients

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **the report distributed via email or file drop (or equivalent)**,
so that **the intended audience receives it on schedule** (FR19).

## Acceptance Criteria

1. **Given** configuration that identifies **R&D** and **marketing** recipients and a **distribution channel** (at least one concrete path for MVP—see tasks)  
   **When** distribution runs **after** the insight report artifact exists for **`run_id`**  
   **Then** each configured recipient **role** receives the report **or** a **durable pointer** (absolute path written in a manifest or log, or attachment path) that an operator can audit.

2. **Given** a distribution **failure** (missing directory, SMTP error, invalid config)  
   **When** the failure occurs  
   **Then** the failure is **logged** with an **actionable** **`error_type`/`error_summary`-style** message (NFR-R1 alignment—not a silent skip) and the pipeline outcome remains **definable** (story: prefer **complete delivery stage** with **`distribution_outcome`** = failed + logged, unless product chooses fail-fast—document the choice in README).

3. **Given** practice / offline deployments  
   **When** distribution is **disabled** or set to **no-op** via configuration  
   **Then** behavior is **explicit** in logs (e.g. `distribution_skipped` with reason) so demos are honest.

## Tasks / Subtasks

- [x] **Configuration** — `pharma_rd/pharma_rd/config.py` + **`pharma_rd/.env.example`**:
  - [x] Add settings for FR19, e.g. **`distribution_channel`** (literal: at minimum **`file_drop`** \| **`none`**; optional **`smtp`** if you implement it in this story) — **snake_case** env **`PHARMA_RD_*`**.
  - [x] Recipient addressing: e.g. **`rd_recipient_email`**, **`marketing_recipient_email`** (for SMTP) **and/or** **`distribution_drop_dir`** (directory root where per-run copies or manifest land) — **do not** commit secrets; document placeholders only.
  - [x] Validate combinations at settings load or at distribution time with **clear** `ValueError` messages (no secrets in exception strings).

- [x] **Distribution logic** — Prefer **`pharma_rd/pharma_rd/integrations/`** or a small **`pharma_rd/pharma_rd/distribution/`** module (architecture: outbound I/O centralized) [Source: `_bmad-output/planning-artifacts/architecture.md` — Integrations]:
  - [x] **File-drop MVP (recommended):** copy **`{artifact_root}/{run_id}/delivery/report.md`** (from story 7.1) into a **stable layout** under **`distribution_drop_dir`**, e.g. **`{drop_dir}/{run_id}/report.md`** or a **`manifest.json`** listing paths for R&D vs marketing — **do not** invent new report formats; reuse the Markdown file.
  - [x] **Optional SMTP:** if implemented, use **stdlib** `smtplib` or existing HTTP patterns; **never** log raw credentials; attach **report.md** or send **secure link** text—pick one and test it.
  - [x] Map **R&D** vs **marketing** roles to **two** distinct destinations (two subdirs, two manifest entries, or two email To/CC) per AC.

- [x] **Wire into Delivery stage** — `pharma_rd/pharma_rd/agents/delivery.py` (or runner hook immediately after `run_delivery` returns):
  - [x] Invoke distribution **after** `report.md` exists (7.1 order preserved).
  - [x] Extend **`DeliveryOutput`** (bump **`schema_version`** to **3**) with **additive** fields such as **`distribution_channel`**, **`distribution_status`** (e.g. **`ok`** \| **`failed`** \| **`skipped`**), optional **`distribution_detail`** (short, non-secret)—**`extra="forbid"`** on models.
  - [x] **Do not** re-render or alter **`report.md`** content during distribution.

- [x] **Logging** — Structured lines with **`event`** (e.g. **`distribution_complete`** / **`distribution_failed`** / **`distribution_skipped`**) and allowlisted **`extra`** keys in `pharma_rd/pharma_rd/logging_setup.py` (e.g. **`distribution_channel`**, **`distribution_status`**).

- [x] **Tests** — `pharma_rd/tests/` (new **`test_distribution.py`** or under **`tests/agents/test_delivery.py`**):
  - [x] **File-drop:** tmp dirs → assert both role targets receive the artifact or manifest pointer; deterministic paths.
  - [x] **Failure:** missing drop dir or permission → assert log-friendly error path (caplog or structured capture pattern used elsewhere).
  - [x] **`tests/pipeline/test_contracts.py`:** **`DeliveryOutput`** v3 round-trip / defaults; legacy v2 JSON loads with safe defaults for new fields.

- [x] **README** — FR19: distribution channels, env vars, artifact paths, relation to **7.3** (read/open).

## Dev Notes

### Requirements mapping

| Source | Notes |
|--------|--------|
| **FR19** | Distribute to **R&D** and **marketing**; channel implementation-open. |
| **NFR-R1** | Actionable failures—visible, classified. |
| **NFR-S1** | Secrets via env only; never log tokens/passwords. |

### Architecture compliance

- **Integrations** / I/O at **`integrations/*`** or dedicated module; **Delivery** stays thin [Source: architecture — boundaries].
- **Persistence:** if you record distribution outcome, prefer **existing** run/stage patterns—avoid ad-hoc DB writes from agents unless the repo already uses injected repos.

### File structure (expected touch list)

| Area | Paths |
|------|--------|
| Config | `pharma_rd/pharma_rd/config.py`, `pharma_rd/.env.example` |
| Distribution | `pharma_rd/pharma_rd/integrations/…` or `pharma_rd/pharma_rd/distribution/` |
| Contracts | `pharma_rd/pharma_rd/pipeline/contracts.py` (`DeliveryOutput`) |
| Delivery | `pharma_rd/pharma_rd/agents/delivery.py` |
| Runner | `pharma_rd/pharma_rd/pipeline/runner.py` (only if hook must live outside `run_delivery`) |
| Logging | `pharma_rd/pharma_rd/logging_setup.py` |
| Tests | `pharma_rd/tests/…` |
| Docs | `pharma_rd/README.md` |

### Previous story intelligence (7.1)

- Report path: **`{run_id}/delivery/report.md`**; **`DeliveryOutput`** v2 has **`report_relative_path`**, **`report_byte_size`** — **extend**, do not break.
- **`run_delivery(run_id, synthesis, artifact_root)`** — distribution likely needs **`artifact_root`**, **`run_id`**, and **`get_settings()`**.

### Technical requirements (guardrails)

- **Ruff** 88; **Pydantic v2**; **no new heavy deps** unless justified (stdlib-first for SMTP).
- **Deterministic** tests (no network in default CI—use **tmp_path** or mocks).

### Project structure notes

- Package root **`pharma_rd/pharma_rd/`**; follow existing **`tests/fixtures/`** if needed.

### Git intelligence

- Mirror **`httpx`** client patterns only if adding HTTP; file-drop uses **`pathlib`/`shutil`**.

### Latest tech / deps

- Python **3.12**.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

— 

### Completion Notes List

- **`DeliveryOutput` v3** with **`distribution_channel`**, **`distribution_status`**, **`distribution_detail`**; **`integrations/report_distribution.py`** implements **`none`** (logged skip), **`file_drop`** (copy to **`rd/{run_id}/`**, **`marketing/{run_id}/`**, **`manifest.json`** under **`{drop}/{run_id}/`**), **`smtp`** (not implemented — **`distribution_failed`** / **`smtp_not_implemented`**).
- Avoided circular import: distribution module does **not** import **`pipeline.contracts`** (package **`__init__`** loads runner → delivery).
- **README** documents **complete delivery stage** with **`distribution_status=failed`** on distribution errors (not fail-fast), per product question.
- Invalid combos (e.g. **`file_drop`** without drop dir) are surfaced at distribution time via **`distribution_failed`** logs and **`distribution_detail`**, not **`ValueError`**, so the delivery artifact still persists.
- **Code review (2026-04-05):** **`_run_id_is_safe()`** rejects path-traversal **`run_id`** values for **`file_drop`** (structured log **`error_type`** = **`invalid_run_id`**).

### File List

- `pharma_rd/pharma_rd/integrations/report_distribution.py` (new)
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/pharma_rd/pipeline/contracts.py` (already extended in branch)
- `pharma_rd/pharma_rd/config.py` (already extended in branch)
- `pharma_rd/.env.example`
- `pharma_rd/README.md`
- `pharma_rd/tests/integrations/test_distribution.py` (new)
- `pharma_rd/tests/agents/test_delivery.py`
- `pharma_rd/tests/pipeline/test_contracts.py`
- `pharma_rd/tests/pipeline/test_logging.py`

### Review Findings

- [x] [Review][Patch] Reject or normalize unsafe **`run_id`** values before building paths (`base / "rd" / run_id`, `marketing`, manifest dir). A **`run_id`** containing **`..`** or path separators can make **`Path.resolve()`** leave the intended drop tree (writes and manifest pointers outside **`distribution_drop_dir`**). Add a small guard (e.g. single path segment, no **`..`**, no `/` or `\\`) and **`distribution_failed`** with **`error_type=invalid_run_id`** (or similar) + test — `pharma_rd/pharma_rd/integrations/report_distribution.py`. **Resolved:** **`_run_id_is_safe()`**, **`error_type=invalid_run_id`**, **`test_distribute_file_drop_rejects_unsafe_run_id`**.

- [x] [Review][Defer] **`manifest.json`** has no **`schema_version`**; optional future hardening for consumers — deferred, pre-existing MVP scope.

## References

- Epic 7 / Story 7.2: `_bmad-output/planning-artifacts/epics.md`
- PRD FR19, NFR-R1: `_bmad-output/planning-artifacts/prd.md`
- Architecture — Delivery & integrations: `_bmad-output/planning-artifacts/architecture.md`
- Prior: `_bmad-output/implementation-artifacts/7-1-render-structured-insight-report-artifact.md`

### Questions (optional — product)

1. **Fail-fast vs complete-with-failed-distribution:** if SMTP fails, should the **run** still mark **delivery** completed? Story asks for an explicit README decision—default to **complete** with **`distribution_status=failed`** unless PM says otherwise.

---

**Story completion status:** done — code review patch applied (2026-04-05); **`uv run ruff check`** and **`uv run pytest`** passing (135 tests).
