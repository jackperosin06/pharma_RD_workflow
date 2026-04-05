# Story 8.4: Practice mode without enterprise SSO

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **workflow operator**,
I want **the system to run in practice mode on public/mock data without SSO**,
so that **we can demo before enterprise IdP** (FR26).

## Acceptance Criteria

1. **Given** a **`practice`** (or equivalent) **deployment profile** is enabled in configuration  
   **When** the process loads settings and runs the pipeline  
   **Then** **no enterprise SSO** is **required** for operation (FR26; MVP has **no** SSO implementation—profile must be **explicit**, documented, and **not** imply IdP hooks)

2. **Given** the practice profile  
   **When** structured logging runs  
   **Then** operators can see **which profile** is active (extend existing JSON log keys where appropriate—`practice_mode` already exists on consumer logs per `logging_setup.JsonLineFormatter` optional fields)

3. **Given** mock or public sources are used (per-stage `practice_mode`, fixture paths, or built-in mocks—e.g. consumer `practice_consumer_mock`, `practice://` sources)  
   **When** configuration is inspected (`get_settings()` / env)  
   **Then** the **practice profile** and **mock/public** usage are **labeled** in **`Settings`** field descriptions and **operator docs** (`pharma_rd/README.md`, `pharma_rd/.env.example`)

4. **Given** the practice profile  
   **When** Delivery renders **`report.md`** / **`report.html`**  
   **Then** include a **clear, optional** line in the **Run summary** (or equivalent prominent block) stating **practice build / public–mock data** and **no enterprise SSO** (FR26 alignment)—must not break **`readability.validate_readable_insight_report`** section markers (`## Run summary`, `## Ranked opportunities`, `## Governance and disclaimer`)

5. **Given** **CI**  
   **When** tests run  
   **Then** unit tests cover **profile parsing**, **invalid** profile rejection (if constrained), and **report snippet** presence when profile is practice

## Tasks / Subtasks

- [x] Add **`deployment_profile`** (or align **`env`** with a constrained **`Literal[...]`**) in `pharma_rd/pharma_rd/config.py` — default **`practice`** for FR26; document that **enterprise SSO** is **out of scope** until FR34 (see PRD roadmap)

- [x] On pipeline start (e.g. `main.py` / runner entry), emit **one structured INFO log** with **`deployment_profile`** (and reuse **`practice_mode`** patterns from consumer where relevant)

- [x] **`delivery.py`** — `_render_markdown` / `_render_html`: conditional **Run summary** line for practice profile; keep headings compatible with `pharma_rd/readability/insight_report.py`

- [x] **`README.md`** + **`.env.example`** — FR26: practice profile, no SSO for MVP, pointer to FR34 enterprise path

- [x] **`tests/test_config.py`** (+ delivery/readability tests if needed) — profile validation; report content when practice

- [x] Run **ruff** + **pytest**; update **sprint-status** story row when moving to **review** (dev workflow)

## Dev Notes

### Problem shape

Epic 8 already wires **partial** FR26 behavior: **`practice_consumer_mock`**, **`ConsumerOutput.practice_mode`**, **`integration_notes`** citing FR26, and log formatter support for **`practice_mode`**. Story **8.4** **unifies** this under an explicit **deployment / practice profile** so operators and report readers see **one** consistent story: **demo-safe, public/mock-capable, no SSO**.

**Non-goals:** Implement SAML/OIDC, user directories, or secrets vault (FR34 / Phase 2).

### Architecture compliance

- [Source: `_bmad-output/planning-artifacts/architecture.md`] **Practice MVP:** public/mock feeds; **no** enterprise SSO for FR26. **Config by environment:** `.env` with explicit profile names.
- [Source: `_bmad-output/planning-artifacts/prd.md`] **FR26** — practice mode using public/mock without enterprise SSO; **FR34** explicitly future.

### Code touchpoints (expected)

| Area | File(s) | Notes |
|------|---------|--------|
| Settings | `pharma_rd/pharma_rd/config.py` | New or constrained profile field; document relationship to **`practice_consumer_mock`** |
| Entry / logging | `pharma_rd/pharma_rd/main.py`, `pharma_rd/pharma_rd/pipeline/runner.py` | Single log line with profile at run start |
| Delivery | `pharma_rd/pharma_rd/agents/delivery.py` | Run summary banner for FR26 |
| Docs | `pharma_rd/README.md`, `pharma_rd/.env.example` | Operator-facing FR26 |
| Tests | `pharma_rd/tests/test_config.py`, delivery tests under `pharma_rd/tests/agents/` | No regression on insight report structure |

### Testing requirements

- Follow existing patterns: **`get_settings.cache_clear()`** in config tests after env mutation
- If adding HTML/Markdown fragments, assert substrings without brittle full-file matches
- **`validate_readable_insight_report`** must still pass for generated reports in tests that use it

### Library / version notes

- **Pydantic v2** + **pydantic-settings** — match existing `Settings` patterns (`Field`, `Literal` if used)
- No new runtime dependencies expected

## Previous story intelligence (8.3)

- **8.3** added **`_validate_http_url`**, strict **https** for Slack, FR25 docs — **preserve** URL validation; practice profile docs should **not** weaken NFR-S1
- Files touched in 8.3: `config.py`, `test_config.py`, `README.md`, `.env.example` — **extend** rather than fork patterns

## Git intelligence

Recent **`git log --oneline`** shows older epic batch commits; **local working tree** may contain **newer** Epic 5–8 work. **Rebase implementation on current `config.py` and `delivery.py`** in the workspace, not only on last commit message.

## Latest technical specifics (2026)

- **FR26** is satisfied by **explicit configuration + labeling**, not by adding an IdP client
- If **`env`** field is already used for unrelated semantics, prefer a **new** `deployment_profile` (or `PHARMA_RD_DEPLOYMENT_PROFILE`) to avoid breaking existing **`PHARMA_RD_ENV`** consumers—**grep** before overloading **`env`**

## Project context reference

No `project-context.md` found in repo; rely on **`architecture.md`**, **`prd.md`**, and this story.

## Dev Agent Record

### Agent Model Used

Cursor (GPT-5.1)

### Debug Log References

### Completion Notes List

- Implemented **`PHARMA_RD_DEPLOYMENT_PROFILE`** (`practice` \| `staging` \| `production`, default **`practice`**) with normalized env parsing.
- **`run_started`** / **`pipeline_resume`** JSON logs include **`deployment_profile`**; formatter allows the key in **`logging_setup`**.
- Delivery **Run summary** includes an FR26 deployment line when profile is **`practice`**; staging test omits it; **`validate_readable_insight_report`** unchanged.
- **`ruff check`** + full **`pytest`** (156 tests) passed.
- Code review: **`test_pipeline_resume_emits_deployment_profile_in_json`** in **`test_logging.py`** (FR26 / `pipeline_resume` log).

### File List

- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/pharma_rd/logging_setup.py`
- `pharma_rd/pharma_rd/pipeline/runner.py`
- `pharma_rd/pharma_rd/agents/delivery.py`
- `pharma_rd/README.md`
- `pharma_rd/.env.example`
- `pharma_rd/tests/test_config.py`
- `pharma_rd/tests/test_smoke.py`
- `pharma_rd/tests/pipeline/test_logging.py`
- `pharma_rd/tests/agents/test_delivery.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/8-4-practice-mode-without-enterprise-sso.md`

### Change Log

- 2026-04-05: Story 8.4 — deployment profile (FR26), pipeline log + delivery report labeling, docs and tests; sprint → review.
- 2026-04-05: Code review — `test_pipeline_resume_emits_deployment_profile_in_json`; sprint → done.

### Review Findings

- [x] [Review][Patch] Assert `deployment_profile` on the `pipeline_resume` JSON log line (README documents it next to `run_started`; `test_logging` currently only checks `run_started`) [`pharma_rd/tests/pipeline/test_logging.py`]

## References

- Epic 8 / Story 8.4: `_bmad-output/planning-artifacts/epics.md` (lines ~696–708)
- FR26, FR34: `_bmad-output/planning-artifacts/prd.md`
- Architecture (practice MVP, config profiles, optional API key for FR32 later): `_bmad-output/planning-artifacts/architecture.md`
- Consumer FR26 slice: `pharma_rd/pharma_rd/agents/consumer.py`, `pharma_rd/pharma_rd/pipeline/contracts.py` (`ConsumerOutput.practice_mode`)
- Logging optional fields: `pharma_rd/pharma_rd/logging_setup.py`
- Report structure: `pharma_rd/pharma_rd/readability/insight_report.py`, `pharma_rd/pharma_rd/agents/delivery.py`

---

**Story completion status:** done — code review complete; patch applied
