# Deferred work (from reviews and planning)

## Deferred from: code review of 6-5-gpt-powered-synthesis.md (2026-04-05)

- **Synthesis GPT repair prompt duplicates full user payload** — Bounded retry appends the entire upstream JSON again; fine for MVP; revisit if operators hit rate limits or timeouts on validation failures.

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

## Deferred from: code review of 3-1-discover-and-summarize-clinical-trial-publications-for-configured-tas.md (2026-04-05)

- *(Superseded 2026-04-05)* **Abstract summary truncation note** — Implemented: `data_gaps` records per-PMID truncation when summaries exceed 800 characters.

## Deferred from: code review of story 3-2 (2026-04-05)

- **Unbounded `*.json` count per directory** — Per-file byte cap exists; optional max file count or batching if operators point large trees at the loader.

- **PubMed `ConnectorFailure` fails the stage** — Internal research degrades without raising; PubMed path still fails the clinical stage on connector errors. Broader “complete with gaps” for outbound HTTP may be a follow-up if product wants NFR-I1 parity for network faults.

## Deferred from: code review of story 4-1 (2026-04-05)

- **Unbounded `*.json` under competitor fixture directory** — Optional max file count or batching if operators attach very large trees.

- **OpenFDA `drugsfda` response shape** — Validate `application_number` / nested structures against live API responses over time; adjust mapper if FDA changes fields.

## Deferred from: code review of 4-3-patent-filing-flags.md (2026-04-05)

- **Downstream stages still stub** — `ConsumerOutput` / `SynthesisOutput` do not consume `patent_filing_flags` yet; expected until later epics wire synthesis and reporting to competitor output.

## Deferred from: code review of 5-3-unmet-need-and-demand-signals.md (2026-04-05)

- **`_resolve_config_path` duplication** — `unmet_need_demand.py` repeats the same path-resolution helper as other integration modules; optional shared util when integrations are next refactored.

## Deferred from: code review of 6-1-consume-monitoring-agent-outputs-for-a-run.md (2026-04-06)

- **Artifact load error consistency** — Synthesis uses `read_stage_artifact_model` for operator-oriented errors; earlier stages still use `read_artifact_bytes` + validate inline. Optional refactor to one helper for all stage reads.

## Deferred from: code review of 6-2-ranked-opportunities-with-cross-domain-cross-reference.md (2026-04-05)

- **v2 synthesis JSON replay** — Loading older `schema_version` 2 synthesis artifacts with the v3 `SynthesisOutput` model can populate default `ranking_criteria_version` and empty or default-ranked lists, misrepresenting whether FR15 ran historically; add explicit migration or README operator note if replay is required.

- **README scope** — Epic 5 consumer configuration and schema bullets landed in the same branch diff as Epic 6 synthesis; fine for an integration branch; isolate commits per epic if you need clean story-to-diff traceability.

## Deferred from: code review of 6-3-evidence-references-and-commercial-viability-per-item.md (2026-04-06)

- **Legacy `SynthesisOutput` v3 on disk** — Artifacts without FR16/FR17 fields require re-run or explicit migration for consumers expecting evidence rows; README calls this out; optional migration utility deferred.

## Deferred from: code review of 6-4-quiet-run-and-scan-summary-transparency-in-synthesis-output.md (2026-04-05)

- **88-character clip on `scan_summary_lines`** — Long therapeutic-area lists or many distinct `pub_src` / `pipe_scopes` values may be truncated with `…`; acceptable MVP; split across extra lines or raise cap if operators report lost scope detail.

## Deferred from: code review of 7-3-recipients-open-and-read-the-report.md (2026-04-05)

- **Markdown vs HTML render paths duplicate structure** — `_render_markdown` and `_render_html` in `delivery.py` mirror content; `insight_report._MARKDOWN_SECTION_MARKERS` must stay aligned with markdown headings. Optional refactor: shared section constants or one render pipeline emitting both formats.

## Deferred from: code review of 7-5-slack-webhook-delivery.md (2026-04-05)

- **`config.py` mixed epic settings on branch** — The same working tree bundles Slack webhook fields with consumer/pharmacy/unmet/distribution and other settings; acceptable on an integration branch; use per-story commits or narrower diffs if you need strict traceability from story ID to files changed.

## Deferred from: code review of 7-2-distribute-report-to-r-d-and-marketing-recipients.md (2026-04-05)

- **`manifest.json` without schema version** — MVP manifest lists paths and `run_id`; add `schema_version` or `$schema` later if external tools need stable parsing.

## Deferred from: code review of 8-1-therapeutic-area-scope-configuration.md (2026-04-05)

- **Verbose `ValidationError` stderr** — Optional single-line operator message derived from `e.errors()` instead of full `str(e)`.

- **Mixed-scope branch** — Epic 5–7 edits bundled with FR23 in the same diff; use narrower commits/PRs when traceability matters.

## Deferred from: code review of 8-2-competitor-watchlists-and-identifiers.md (2026-04-06)

- **Shared normalizer helper** — Optional refactor so FR23 and FR24 comma-list validation share one implementation with injectable regex and env var name for errors.

- **Apostrophe / extra punctuation in competitor labels** — Current `_COMPETITOR_LABEL_RE` may reject some legal entity spellings; extend character class or document limitation.

- **Mixed-scope branch** — Non–8.2 changes may appear in the same diff as FR24 work; prefer focused commits when needed.

## Deferred from: code review of 3-3-gpt-powered-clinical-analysis.md (2026-04-05)

- **Third-party OpenAI/HTTP loggers at DEBUG** — Deployment logging policy should ensure `openai` / HTTP client loggers are not left at DEBUG if request bodies could leak MNPI; application code does not log full prompts.

## Deferred from: code review of 4-4-gpt-powered-competitor-analysis.md (2026-04-05)

- **Urgent-attention flag vs severity consistency** — If the model returns mismatched **`urgent_attention_flag`** and **`urgent_attention_severity`**, optional normalization when synthesis (**6.5**) consumes **`CompetitorGptAnalysis`**.

- **Large competitor GPT payloads** — No explicit token/context cap before OpenAI call; shared hardening with clinical/consumer GPT paths if fixture-driven runs grow very large.

## Deferred from: code review of 5-4-gpt-powered-consumer-insight-analysis.md (2026-04-05)

- **AC4 test depth** — Optional: assert **`call_consumer_gpt_analysis`** call shape or **`_payload_for_prompt`** keys when mocking, beyond merge success/failure.

- **Large consumer GPT payloads** — Same token/context cap theme as other GPT integration stories when JSON payloads grow very large.
