# pharma_rd (application)

Python package for the **pharma_RD** multi-agent pipeline. This directory is the **uv** project root (nested under the `pharma_RD_workflow` monorepo).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`, or `pip install uv`)

## Setup

From this directory (`pharma_rd/`):

```bash
uv sync --all-groups
```

Uses **Python 3.12** (see `.python-version`). The lockfile is `uv.lock`.

## Run

```bash
uv run pharma-rd
# or
uv run python -m pharma_rd
```

## Lint & test (matches CI)

```bash
uv run ruff check .
uv run pytest
```

## Configuration

- Copy `.env.example` to `.env` for local overrides. Use **non-secret** keys only; real secrets stay out of git (NFR-S1).
- Settings use the `PHARMA_RD_` prefix (see `pharma_rd/config.py`).
- **Database:** `PHARMA_RD_DB_PATH` (default `data/app.db`) — SQLite file for run/stage history; parent directory is created on open. Schema DDL and version live in `pharma_rd/persistence/db.py` (`PRAGMA user_version`). **v2+** adds `stage_artifacts` (path + SHA-256 per stage output).
- **Artifacts:** `PHARMA_RD_ARTIFACTS_ROOT` (default **`artifacts/`** under cwd) — JSON blobs per run/stage at `{root}/{run_id}/{stage_key}/output.json`; metadata in `stage_artifacts`. Default folder is gitignored.
- **Retention:** `PHARMA_RD_RETENTION_DAYS` (default **30**) — use `purge_runs_older_than()` from `pharma_rd.persistence` to delete runs older than this window (cascades stages and artifact rows).
- **Pipeline:** Ordered stages **clinical → competitor → consumer → synthesis → delivery**; contracts in `pharma_rd/pipeline/contracts.py`, orchestration in `pharma_rd/pipeline/runner.py` (`run_pipeline`).

## Layout note

The import package lives at `pharma_rd/pharma_rd/` (flat layout). This matches a normal editable install on all platforms; a future story may align folder names with the architecture doc’s `src/` sketch without changing import paths.

## CI

GitHub Actions workflow: `.github/workflows/ci.yml` at the **repository root** (not inside this folder). It sets `working-directory: pharma_rd` and runs `uv sync --all-groups --frozen`, `ruff check`, and `pytest`—same commands as above.
