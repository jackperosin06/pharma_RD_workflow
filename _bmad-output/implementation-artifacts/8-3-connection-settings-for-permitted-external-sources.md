# Story 8.3: Connection settings for permitted external sources

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **connection settings for permitted APIs, files, and stubs to be explicit, validated, and documented per deployment**,
so that **integrations use consistent timeouts and base URLs** and **secrets stay out of repo and structured logs** (FR25, NFR-S1).

## Acceptance Criteria

1. **Given** **non-secret** connector settings in **`PHARMA_RD_*`** (timeouts, base URLs for outbound HTTP)  
   **When** **`Settings`** loads  
   **Then** **HTTP(S) base URLs** used by connectors (e.g. PubMed E-utilities, OpenFDA, optional probe, Slack webhook) are **parseable** with **http** or **https** scheme and a **non-empty host** — invalid values **fail at load** with a clear validation message.

2. **Given** **`PHARMA_RD_SLACK_WEBHOOK_URL`** is set  
   **When** settings validate  
   **Then** the URL **must** use **`https://`** (Slack incoming webhooks; NFR-S1).

3. **Given** **NFR-S1**  
   **When** operators configure the deployment  
   **Then** documentation states that **secrets** are **not** stored in git-tracked `.env` examples as real values; **connector HTTP** does not log request bodies or tokens (existing **`http_client`** behavior preserved).

4. **Given** **CI**  
   **When** tests run  
   **Then** unit tests cover **invalid** URL rejection and **valid** defaults.

5. **Given** **documentation**  
   **When** an operator reads **`pharma_rd/README.md`** and **`.env.example`**  
   **Then** they see **FR25** — which keys control **timeouts / retries / backoff** and **which URLs** apply to which integrations.

## Tasks / Subtasks

- [x] Add **`_validate_http_url`** (or equivalent) and **`field_validator`** on **`pubmed_eutils_base`**, **`openfda_drugsfda_url`**, **`connector_probe_url`** (when non-**None**), **`slack_webhook_url`** (**https** only when set).

- [x] **`README.md`** + **`.env.example`** — FR25 summary: HTTP connector settings + URL keys; NFR-S1 secret hygiene pointer.

- [x] **`pharma_rd/tests/test_config.py`** — invalid URL env cases; **`get_settings.cache_clear()`**.

- [x] Run **ruff** + **pytest**; story → **review**.

## Dev Notes

- **Existing:** `http_client.request_with_retries` reads **`http_timeout_seconds`**, **`http_max_retries`**, **`http_retry_backoff_seconds`** from **`get_settings()`** (story 2.2).
- **Do not** add new secrets to **`Settings`**; optional future API keys belong in separate env vars, not committed.

## Dev Agent Record

### Agent Model Used

Cursor (AI coding agent)

### Debug Log References

### Completion Notes List

- Added **`_validate_http_url`** and **`field_validator`** (after) on **`pubmed_eutils_base`**, **`openfda_drugsfda_url`**, **`connector_probe_url`**, **`slack_webhook_url`** (Slack requires **https**).
- README **Connection settings (Epic 8 / FR25)** bullet; `.env.example` FR25 comments on URL keys.
- Tests: invalid PubMed/OpenFDA/Slack URLs; CLI invalid **`PHARMA_RD_PUBMED_EUTILS_BASE`**.

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/tests/test_cli.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/8-3-connection-settings-for-permitted-external-sources.md`

### Change Log

- 2026-04-06: Story 8.3 — FR25 URL validation, docs, tests; sprint → review.
- 2026-04-05: Code review — added `test_connector_probe_url_invalid_raises`; sprint → done.

### Review Findings

- [x] [Review][Patch] Add unit test for invalid non-empty `PHARMA_RD_CONNECTOR_PROBE_URL` (AC1 lists optional probe alongside PubMed/OpenFDA/Slack) [`pharma_rd/tests/test_config.py`]

## References

- Epic 8 / Story 8.3: `_bmad-output/planning-artifacts/epics.md`
- FR25, NFR-S1: `_bmad-output/planning-artifacts/prd.md`
- `pharma_rd/pharma_rd/http_client.py`, `pharma_rd/pharma_rd/config.py`

---

**Story completion status:** done — code review complete; patch applied
