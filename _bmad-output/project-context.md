---
project_name: pharma_RD_workflow
user_name: Jackperosin_
date: "2026-04-05T00:00:00Z"
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - quality_rules
  - workflow_rules
  - anti_patterns
status: complete
rule_count: 42
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

**Code root:** `pharma_rd/` (run `uv run pytest`, `uv run pharma-rd`, etc. from this directory unless docs say otherwise.)

---

## Technology Stack & Versions

| Area | Standard |
|------|-----------|
| **Python** | **3.12+** (pinned in `pharma_rd/.python-version`) |
| **Tooling** | **`uv`** — dependencies in `pharma_rd/pyproject.toml` + `pharma_rd/uv.lock` |
| **Validation** | **Pydantic v2** for stage outputs, config (`pydantic-settings`), API payloads |
| **HTTP** | **httpx** with shared **`request_with_retries`** (`http_client.py`) — timeouts, bounded retries, backoff; **NFR-I2** classifications (`IntegrationErrorClass`) |
| **Scheduler** | **APScheduler** (`scheduler.py`) for recurring runs |
| **LLM** | **openai** SDK (v1.x–2.x per lock); never call OpenAI without tests mocking the client |
| **HTML safety** | **nh3** for sanitizing GPT-produced HTML before distribution |
| **Persistence** | **SQLite** (`persistence/db.py`) + filesystem **artifact root** (`persistence/artifacts.py`) |
| **Lint / test** | **Ruff** target py312, rules `E`, `F`, `I`, `UP` — **pytest** 8+, `testpaths = ["tests"]`, `pythonpath = ["."]` |

**Version constraints:** Prefer exact ranges already in `pyproject.toml`; bump only with `uv lock` and CI green.

---

## Critical Implementation Rules

### Language-Specific Rules (Python)

- Use **`from __future__ import annotations`** in new modules when the codebase already does for consistency.
- **Public contracts** for pipeline stages live in **`pipeline/contracts.py`** (Pydantic models); keep JSON field names **`snake_case`** to match Python and PRD architecture.
- **Settings:** `pharma_rd.config.get_settings()` — cached; tests must **`get_settings.cache_clear()`** when env is patched (see `conftest.py`).
- **Logging:** Use **`get_pipeline_logger`** / pipeline context (`logging_setup.py`). Logs are **one JSON object per line** to stdout with **`run_id`**, **`correlation_id`** (defaults to `run_id`), **`stage`**, **`agent`**, optional **`event`** / **`outcome`**. Do not log secrets, full API keys, or raw PHI.
- **Pipeline context:** Set run/stage context when adding new entrypoints so log lines stay correlated (contextvars in `logging_setup`).
- Prefer **typed** signatures and explicit **`StrEnum`** for fixed string domains (e.g. `IntegrationErrorClass`).

### Framework-Specific Rules (pipeline / agents)

- **Stage order** is defined by the product (`pipeline/order.py` / runner); do not reorder without PRD/architecture alignment.
- **Agents** live under **`pharma_rd/agents/`**; **external API connectors** under **`pharma_rd/integrations/`** — keep I/O and HTTP out of pure ranking/synthesis logic where possible.
- **OpenAI:** Shared client patterns in **`integrations/openai_*.py`**; respect env vars from **`config.py`** / `.env.example` (e.g. `PHARMA_RD_OPENAI_API_KEY`); **mock** in tests.
- **Delivery / reports:** Human-judgment disclaimers (**FR22**); GPT HTML flows through **sanitize** (`report_html_sanitize.py`) before Slack or file delivery.
- **Access control:** `access_control.py` — coarse MVP behavior; do not weaken without explicit story.

### Testing Rules

- **Autouse fixtures** in `conftest.py` force **deterministic synthesis** and **template renderer** unless a test overrides env — avoid accidental real OpenAI/HTTP in CI.
- **Mock httpx / OpenAI** at boundaries; prefer testing **Pydantic parse** and **runner behavior** with fixtures under `tests/fixtures/`.
- Mirror package layout: `tests/agents/`, `tests/pipeline/`, `tests/integrations/`, etc.
- New behavior needs tests that fail if contracts or log fields regress (especially persistence and stage outcomes).

### Code Quality & Style Rules

- **Ruff** is the source of truth; fix `E`, `F`, `I`, `UP` before merge.
- **Imports:** isort-compatible grouping (ruff handles `I`).
- **Naming:** `snake_case` modules/functions; Pydantic models **`PascalCase`**; test files `test_*.py`.
- **Docstrings:** Add for public APIs when behavior is non-obvious; avoid redundant comments on every line.
- **Secrets:** Only via environment / pydantic-settings — **`.env` gitignored**; **`.env.example`** documents keys without values.

### Development Workflow Rules

- Run **`uv run ruff check pharma_rd`** and **`uv run pytest`** from `pharma_rd/` before considering work done.
- CI expectation (per architecture): **lint + tests** on PR (e.g. GitHub Actions).
- **Configuration** for TA scope, watchlists, schedule belongs in **settings / config**, not hardcoded constants in agents.

### Critical Don't-Miss Rules

- **Do not** claim regulatory approval, diagnosis, or autonomous clinical action — product is **decision support**; copy and outputs must keep **pursuit human-owned** (FR22).
- **Do not** skip **citations / evidence** fields where FR16 applies; synthesis and delivery stories assume verifiable references.
- **Do not** retry arbitrary **4xx** HTTP errors — only the statuses in **`_RETRYABLE_STATUS`** (`http_client.py`) plus transient network/timeout behavior.
- **Do not** block the pipeline silently on empty feeds — **NFR-I1**: degrade gracefully, surface transparency (**FR27–FR28**) in structured outputs.
- **Do not** add PHI to logs or prompts in MVP paths; **NFR-S4** assumption is non-PHI unless explicitly scoped.
- **Do not** bypass HTML sanitization for model-generated report HTML shown to users or sent to Slack.

---

## Usage Guidelines

**For AI Agents**

- Read this file before implementing changes in `pharma_rd/`.
- Prefer matching existing modules (`runner`, `contracts`, `integrations`) over new parallel patterns.
- When in doubt, choose the **more restrictive** security and logging rule.

**For Humans**

- Update this file when the stack, env vars, or cross-cutting contracts change.
- Trim rules that become universal/obvious over time; keep the file **lean** for LLM context.

---

Last Updated: 2026-04-05
