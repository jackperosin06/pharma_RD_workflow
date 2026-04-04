# Story 1.1: Initialize project from architecture baseline

Status: done

<!-- Optional: run Validate Story ([VS]) before dev-story for a formal readiness check. -->

## Story

As a **developer**,
I want **the application scaffolded with `uv`, Python 3.12, and core dependencies** under the repo’s Python package layout,
so that **all subsequent pipeline work matches the architecture baseline and CI runs lint + tests on every PR**.

## Acceptance criteria

1. **Given** a clone of `pharma_RD_workflow`, **when** the developer runs the documented commands from the **repository root**, **then** a **`pharma_rd/`** application directory exists with `pyproject.toml`, **`uv.lock`**, and **`.python-version`** pinning **Python 3.12**.
2. **When** the developer runs **`uv run`** (e.g. `uv run python -m pharma_rd` or the configured script entry), **then** the process exits **0** with a minimal runnable entrypoint (no-op or “hello” is acceptable for this story).
3. **Dependencies:** runtime packages include **`pydantic`**, **`pydantic-settings`**, **`httpx`** (versions pinned via `uv.lock`). Dev dependencies include **`pytest`** and **`ruff`** (per architecture: CI runs lint + tests).
4. **Secrets (NFR-S1):** **`.env.example`** exists at **`pharma_rd/.env.example`** (or repo root if you standardize one file—document in README) listing **only non-secret** keys (e.g. `PHARMA_RD_ENV=development`); **no** API keys or tokens in git.
5. **CI:** **`.github/workflows/ci.yml`** runs on PR/push to main: install **`uv`**, sync deps, run **`ruff check`** and **`pytest`** against the `pharma_rd` tree.
6. **README:** **`pharma_rd/README.md`** (or section in root README) documents: install uv, `uv sync`, `uv run …`, and how CI maps to local commands.

## Tasks / subtasks

- [x] Create **`pharma_rd/`** application tree at **repo root** (do not place Python project inside `_bmad-output/`). Use Astral **`uv`** per [Creating projects](https://docs.astral.sh/uv/concepts/projects/init/) (e.g. `uv init pharma_rd` from parent of `pharma_rd`, or equivalent **`--package`** layout). Prefer **`src/pharma_rd/`** layout to match architecture.
- [x] **`uv python pin 3.12`** and verify **`.python-version`** reads `3.12`.
- [x] **`uv add`** `pydantic` `pydantic-settings` `httpx`; **`uv add --dev`** `pytest` `ruff`.
- [x] Add **`pharma_rd/__init__.py`** and **`pharma_rd/main.py`** (flat package under project root) with a trivial entrypoint; wire **`[project.scripts]`** or document `uv run python -m pharma_rd`.
- [x] Add **`pharma_rd/config.py`**: `pydantic-settings` `Settings` class with safe defaults (no secrets); single place for future env loading per architecture enforcement.
- [x] **`.gitignore`** under `pharma_rd/` or repo root: `.venv/`, `__pycache__/`, `.env`, `artifacts/`, `data/`, `*.db` as applicable.
- [x] **`.env.example`** with placeholder keys only.
- [x] **`tests/test_smoke.py`**: one test that imports package or runs a trivial assertion so CI proves pytest works.
- [x] **`.github/workflows/ci.yml`**: `actions/checkout`, `astral-sh/setup-uv` or official uv install, `uv sync --frozen` (or `uv sync`), `uv run ruff check .`, `uv run pytest`.
- [x] **README** with exact commands for macOS/Linux.

## Dev notes

### Scope boundaries (prevent creep)

- **In scope:** Tooling, layout, config skeleton, CI, minimal entrypoint, smoke test.
- **Out of scope for 1.1:** SQLite schema, pipeline runner, agents, API server, artifact directories beyond `.gitignore` entries—those are **1.2+**.

### Repository layout (critical)

The BMad repo root **`pharma_RD_workflow/`** already contains **`_bmad-output/`**, **`.cursor/`**, etc. **Place all Python application code under `pharma_rd/`** at the same level as `_bmad-output/`, not inside planning folders. [Source: `_bmad-output/planning-artifacts/architecture.md` § Project structure and boundaries]

### Architecture compliance

| Topic | Requirement |
|-------|-------------|
| **Starter** | **`uv init`** + **`uv python pin 3.12`**; `pyproject.toml` + **`uv.lock`**. [Source: architecture § Starter Template Evaluation] |
| **Config** | Central **`config.py`** using **`pydantic-settings`**; no scattered `os.environ` in future stories. [Source: architecture § Implementation patterns] |
| **Naming** | Python **snake_case**; future JSON **snake_case**. [Source: architecture § Naming patterns] |
| **CI** | **ruff** + **pytest** on PR. [Source: architecture § Infrastructure; Implementation patterns] |
| **Python** | **3.12** (supported maintenance track; LangGraph and libs expect ≥3.10). |

### Suggested package layout (target end state for Epic 1)

Architecture defines the full tree (`pipeline/`, `agents/`, `persistence/`, …). **Story 1.1** only needs the **skeleton** that does not break later adds:

```
pharma_rd/
├── pyproject.toml
├── uv.lock
├── .python-version
├── README.md
├── .env.example
├── .gitignore
├── src/pharma_rd/
│   ├── __init__.py
│   ├── main.py
│   └── config.py
├── tests/
│   └── test_smoke.py
└── .github/workflows/ci.yml
```

Create **empty package dirs** (`pipeline/`, `agents/`, …) **only if** needed to satisfy imports; otherwise **omit** until stories 1.2–1.3 to avoid empty-package noise.

### Testing requirements

- **pytest** discovers `tests/`.
- **ruff** targets `src/` and `tests/` (configure `pyproject.toml` `[tool.ruff]` if needed).
- One smoke test sufficient for 1.1; coverage thresholds optional later.

### Latest technical notes (uv)

- Prefer official docs: [uv project init](https://docs.astral.sh/uv/concepts/projects/init/), [Working on projects](https://docs.astral.sh/uv/guides/projects/).
- Use **`uv sync`** in CI for reproducible installs from **`uv.lock`**.
- If `uv init` defaults differ (e.g. flat vs `src/`), **normalize to `src/pharma_rd/`** to match architecture before merging.

## Previous story intelligence

- **None** — first implementation story in Epic 1.

## Git intelligence

- Greenfield application under `pharma_rd/`; no prior app commits assumed. Follow patterns established in this story for later work.

## Project context reference

- No **`project-context.md`** in repo; brownfield scan not required.

## Dev agent record

### Agent model used

Composer (Cursor agent)

### Debug log references

- Initial `uv_build` editable install produced `__editable__*.pth` skipped by macOS Python `site.py` (hidden `.pth`); resolved with **setuptools** editable install and **flat package layout** `pharma_rd/pharma_rd/` so imports work in CI and locally.

### Completion notes list

- Implemented **`pharma_rd/`** uv project with Python **3.12**, dependencies **pydantic**, **pydantic-settings**, **httpx**, dev **pytest** + **ruff**.
- **`pharma_rd`**, **`pharma-rd`** console script, **`python -m pharma_rd`** exit 0.
- **`config.py`** with `PHARMA_RD_*` settings and **`.env.example`** (no secrets).
- **CI** at repo root **`.github/workflows/ci.yml`** with `working-directory: pharma_rd`, `uv sync --all-groups --frozen`, `ruff`, `pytest`.
- **`pharma_rd/README.md`** documents local commands and CI parity.

### File list

- `pharma_rd/pyproject.toml`
- `pharma_rd/uv.lock`
- `pharma_rd/.python-version`
- `pharma_rd/.gitignore`
- `pharma_rd/.env.example`
- `pharma_rd/README.md`
- `pharma_rd/pharma_rd/__init__.py`
- `pharma_rd/pharma_rd/__main__.py`
- `pharma_rd/pharma_rd/main.py`
- `pharma_rd/pharma_rd/config.py`
- `pharma_rd/tests/test_smoke.py`
- `.github/workflows/ci.yml`

## Change log

- 2026-04-04: Story 1.1 implemented — uv scaffold, flat package layout, CI, smoke tests.
- 2026-04-04: Code review — decision A (keep flat layout); pyproject description + subprocess smoke for `python -m pharma_rd`; httpx defer; console script not smoke-tested (macOS skips hidden `__editable__*.pth` for setuptools editable installs).

### Review Findings

- [x] [Review][Decision] Package layout (`src/pharma_rd/` vs flat `pharma_rd/pharma_rd/`) — **accepted flat layout for 1.1** (option A); README documents rationale.
- [x] [Review][Patch] Replace placeholder `description` in `pyproject.toml` — fixed.
- [x] [Review][Patch] Subprocess smoke test for `python -m pharma_rd` (AC2) — added in `tests/test_smoke.py`.
- [x] [Review][Defer] `httpx` declared but unused in application code — acceptable until HTTP client is used in later stories; keep dependency per AC3.

---

**Story context:** Ultimate context pass completed — ready for **`bmad-dev-story`** ([DS]).
