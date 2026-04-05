# Story 8.5: Coarse access control for reports and logs

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **organization administrator**,
I want **reports and logs restricted to authorized users or lists**,
so that **insight artifacts are not world-readable** (FR32, NFR-S2).

## Acceptance Criteria

1. **Given** the deployment uses **shared storage** (artifact root, DB, or log output paths) **or** a future **HTTP** surface for reports/history  
   **When** operators configure access control  
   **Then** there is a **documented, coarse** mechanism: **optional shared secret** (e.g. **`Authorization: Bearer`** or **`X-API-Key`** from environment) **and/or** **POSIX-style** restrictions for on-disk paths — aligned with [Source: `_bmad-output/planning-artifacts/architecture.md`] **Practice MVP auth** (no user directory for MVP)

2. **Given** **`PHARMA_RD_*`** settings for access control (token name TBD in implementation — e.g. single **`PHARMA_RD_ARTIFACT_ACCESS_TOKEN`**)  
   **When** **`Settings`** loads  
   **Then** values are **non-secret in examples** (placeholders only in **`.env.example`**); real tokens stay in runtime env only (NFR-S1)

3. **Given** an **unauthenticated** or **wrong-token** access attempt **where the product enforces a guard** (e.g. optional CLI subcommands that read DB/artifacts when protection is enabled, or a minimal HTTP read surface if introduced)  
   **When** the guard runs  
   **Then** access is **denied** with **clear** operator messaging (no token leakage in logs)

4. **Given** **`deployment_profile=practice`**  
   **When** operators follow runbook  
   **Then** a **single shared team key** is an **acceptable** MVP pattern (per epics and architecture); behavior is **documented** in **`pharma_rd/README.md`**

5. **Given** **CI**  
   **When** tests run  
   **Then** unit tests cover **token required / token accepted / missing token** paths for any new guard, and **docs** state scope (what is protected vs still OS-level)

## Tasks / Subtasks

- [x] **`config.py`** — add **optional** access-token (or equivalent) **`Field`**(s) with clear descriptions (FR32, NFR-S2); **no** real secrets in committed examples

- [x] **Guard point(s)** — choose minimal surface: e.g. **`pharma-rd runs`** / **`pharma-rd status`** when env requires token, **and/or** `chmod`/directory guidance for **`PHARMA_RD_ARTIFACTS_ROOT`** / **`PHARMA_RD_DB_PATH`**; **or** stub **`api/deps.py`** only if HTTP is in scope for this increment (prefer smallest change that satisfies AC)

- [x] **`README.md`** + **`.env.example`** — FR32 / NFR-S2: what is protected, practice shared key, OS permissions for shared storage

- [x] **Tests** — `tests/test_cli.py` / `tests/test_config.py` (and new module tests if HTTP deps added)

- [x] Run **ruff** + **pytest**; story → **review** when complete

## Dev Notes

### Problem shape

MVP today is **CLI + SQLite + on-disk artifacts** (see **`pharma_rd/main.py`**, **`operator_queries.py`**). There is **no** production HTTP server in-repo yet; **`poll_status`** text even references a **future** HTTP API. Story **8.5** must still satisfy **FR32 / NFR-S2** by (**a**) **coarse** controls that match architecture (**Bearer / API key from env**), and (**b**) **explicit** documentation for **shared-folder** deployments where OS permissions are the primary control.

**Non-goals:** Full SSO, per-user ACLs, multi-tenant isolation (FR34 / Phase 2).

### Architecture compliance

- [Source: `_bmad-output/planning-artifacts/architecture.md`] **Practice MVP auth** — optional shared secret; **`api/deps.py` or CLI guard**, env token; FR32 coarse access for practice.
- [Source: `_bmad-output/planning-artifacts/prd.md`] **FR32** — mechanism implementation-open; may be coarse in practice builds. **NFR-S2** — reports/logs access-controlled (see FR32).

### Code touchpoints (expected)

| Area | File(s) | Notes |
|------|---------|--------|
| Settings | `pharma_rd/pharma_rd/config.py` | Optional token; validate empty vs set |
| CLI | `pharma_rd/pharma_rd/main.py`, `pharma_rd/pharma_rd/cli.py`, `pharma_rd/pharma_rd/operator_queries.py` | Cheapest guard: **`runs` / `status`** when token env set |
| Docs | `pharma_rd/README.md`, `pharma_rd/.env.example` | Runbook: shared key + directory permissions |
| Tests | `pharma_rd/tests/test_cli.py`, `test_config.py` | Denied vs allowed |

### Testing requirements

- **`get_settings.cache_clear()`** after env changes
- Do **not** print real tokens in assertion failures; use **redacted** or **presence** checks

### Library / version notes

- Stdlib + existing **pydantic** — avoid new web framework unless story scope explicitly expands to HTTP in this increment

## Previous story intelligence (8.4)

- **`deployment_profile`** (`practice` \| `staging` \| `production`) and **`PHARMA_RD_DEPLOYMENT_PROFILE`** — **8.5** should **compose** with practice (**single shared key** in runbooks) without contradicting FR26 “no SSO” messaging
- **`logging_setup`** / structured logs — if guards reject access, log **`event`** with **no secrets**

## Git intelligence

Implement against **current** `main` / workspace **`cli.py`** and **`config.py`**; branch may carry multiple epic diffs.

## Latest technical specifics (2026)

- Prefer **constant-time compare** (`hmac.compare_digest`) if comparing bearer tokens in Python
- **OWASP** — never log bearer tokens; use generic “unauthorized” messages

## Project context reference

No `project-context.md` in repo; use **`architecture.md`**, **`prd.md`**, this story.

## Dev Agent Record

### Agent Model Used

Composer (Cursor agent)

### Debug Log References

_(none)_

### Completion Notes List

- Optional `PHARMA_RD_ARTIFACT_ACCESS_TOKEN` on `Settings`; max length 8192; empty → None.
- `pharma_rd/access_control.py`: `cli_access_exit_code()` uses `hmac.compare_digest` against `PHARMA_RD_CLI_ACCESS_TOKEN` (not loaded via Settings); stderr-only denial messages.
- CLI guards: `run`, `runs`, `status`, `retry-stage` when artifact token set; scheduler calls `execute_pipeline_run(..., enforce_cli_access=False)`.
- README + `.env.example` document scope and shared-storage permissions.
- Tests: CLI denied/allowed, config token length, scheduler kwargs.

### File List

- `pharma_rd/pharma_rd/access_control.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/cli.py`
- `pharma_rd/pharma_rd/scheduler.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `pharma_rd/tests/test_cli.py`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/tests/test_scheduler.py`

## Change Log

- 2026-04-05: Implemented coarse CLI access guard, config field, docs, tests; story status → review.

### Review Findings

- [x] [Review][Patch] Add CLI tests for `status` and `retry-stage` when `PHARMA_RD_ARTIFACT_ACCESS_TOKEN` is set (denied without `PHARMA_RD_CLI_ACCESS_TOKEN`, allowed when tokens match) — AC5 asks for token required / accepted / missing paths for **any** guarded command; current tests cover `runs` and `run` only. [`pharma_rd/tests/test_cli.py`] — fixed 2026-04-05.

- [x] [Review][Patch] Harden `cli_access_exit_code` so `.encode("utf-8")` cannot raise `UnicodeEncodeError` for malformed token strings (deny with generic stderr message instead of crashing the CLI). [`pharma_rd/pharma_rd/access_control.py`] — fixed 2026-04-05; `tests/test_access_control.py` covers non-encodable expected token.

## References

- Epic 8 / Story 8.5: `_bmad-output/planning-artifacts/epics.md` (lines ~711–724)
- FR32, NFR-S2: `_bmad-output/planning-artifacts/prd.md`
- Architecture (Practice MVP auth): `_bmad-output/planning-artifacts/architecture.md`
- CLI operators: `pharma_rd/README.md` (runs / status)

---

**Story completion status:** done — code review findings addressed (2026-04-05).
