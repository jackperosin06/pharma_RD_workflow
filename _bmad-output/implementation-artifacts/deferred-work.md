# Deferred work (from reviews and planning)

## Deferred from: code review of 1-1-initialize-project-from-architecture-baseline.md (2026-04-04)

- **`httpx` unused in application code** — Runtime dependency is required by story AC3 for upcoming HTTP usage; no import until pipeline/external calls land in later stories.

## Deferred from: code review of 1-2-persist-runs-and-stages-in-sqlite.md (2026-04-04)

- **Index on `runs(created_at)`** — Optional for large tables when `purge_runs_older_than` is hot; defer until scale or profiling indicates need.

## Deferred from: code review of 1-3-pipeline-runner-with-ordered-stages-and-artifact-handoffs.md (2026-04-05)

- **Data-driven pipeline loop** — Optional refactor from five explicit stage blocks to a table-driven loop; current code is clear for MVP.

## Deferred from: code review of 1-4-correlation-id-and-structured-logging.md (2026-04-04)

- **`run_started` before `runs.status=running`** — Log line `run_started` precedes `update_run_status(..., "running")`; minor timeline skew for strict DB–log correlation. Reorder logs vs DB or document if it becomes an operator issue.

## Deferred from: code review of 2-2-per-stage-timeouts-and-bounded-retries-for-external-calls.md (2026-04-05)

- **Backoff jitter** — See story file Review Findings [Defer]; optional hardening for upstream protection.
