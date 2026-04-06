"""Human-readable framing for insight reports (gaps + FR28 scan lines).

Operator-oriented ``integration_notes`` are separated from user-facing ``data_gaps``
so the report reads like an executive brief, not a log dump.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pharma_rd.pipeline.contracts import SynthesisOutput

_MAX_COVERAGE_GAPS = 8
_MAX_OPERATOR_NOTES = 3


def partition_upstream_gaps(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split ``[stage] …`` gaps from ``[stage:integration] …`` operator notes."""
    coverage: list[str] = []
    operator: list[str] = []
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        if ":integration]" in s:
            operator.append(s)
        else:
            coverage.append(s)
    return coverage, operator


@dataclass(frozen=True)
class ExecutiveGapSections:
    """Truncated lists for the report body."""

    coverage: list[str]
    operator: list[str]
    coverage_remaining: int
    operator_remaining: int


def build_executive_gap_sections(synthesis: SynthesisOutput) -> ExecutiveGapSections:
    cov, ops = partition_upstream_gaps(synthesis.aggregated_upstream_gaps)
    cov_show = cov[:_MAX_COVERAGE_GAPS]
    ops_show = ops[:_MAX_OPERATOR_NOTES]
    return ExecutiveGapSections(
        coverage=cov_show,
        operator=ops_show,
        coverage_remaining=max(0, len(cov) - len(cov_show)),
        operator_remaining=max(0, len(ops) - len(ops_show)),
    )


def _strip_bracket_label(line: str) -> str:
    """Turn ``[clinical] msg`` into ``Clinical — msg`` for readability."""
    m = re.match(r"^\[([^\]]+)\]\s*(.*)$", line.strip(), re.DOTALL)
    if not m:
        return line
    label, rest = m.group(1), m.group(2).strip()
    return f"{label.replace('_', ' ').title()} — {rest}"


def format_gap_line_for_report(line: str) -> str:
    """Readable gap line: coverage vs operator/integration."""
    s = line.strip()
    if ":integration]" in s:
        m = re.match(r"^\[([^:]+):integration\]\s*(.*)$", s, re.DOTALL)
        if m:
            stage, rest = m.group(1), m.group(2).strip()
            return f"Technical ({stage}): {rest}"
    return _strip_bracket_label(s)


_COMPETITOR_RE = re.compile(
    r"^Competitor:\s*appr=(\d+)\s+disc=(\d+)\s+pipe=(\d+)\s+patents=(\d+)"
    r"(?:\s+pipe_scopes=(.+?))?(?:\s+patent_comp=(.+?))?$"
)
_CONSUMER_RE = re.compile(
    r"^Consumer:\s*practice_mode=(\w+)\s+feedback=(\d+)\s+sales=(\d+)\s+unmet=(\d+)"
    r"(?:\s+sales_scopes=(.+))?$"
)


def _humanize_clinical_scan_line(t: str) -> str | None:
    """Parse ``Clinical: pubs=…`` (see ``synthesis._build_scan_summary``)."""
    if not t.startswith("Clinical:"):
        return None
    body = t[len("Clinical:") :].strip()
    m = re.match(r"pubs=(\d+)\s+internal=(\d+)\s+tas=(.+)$", body)
    if not m:
        return None
    pubs, internal, tail = int(m.group(1)), int(m.group(2)), m.group(3)
    tas = tail
    pub_src: str | None = None
    int_lbl: str | None = None
    if " pub_src=" in tail:
        tas, _, rest = tail.partition(" pub_src=")
        if " internal_lbl=" in rest:
            pub_src, _, int_lbl = rest.partition(" internal_lbl=")
        else:
            pub_src = rest
    elif " internal_lbl=" in tail:
        tas, _, int_lbl = tail.partition(" internal_lbl=")
    tas_phrase = (
        "none configured for PubMed" if tas.strip() == "none" else tas.strip()
    )
    out = (
        f"Clinical — {pubs} publication(s) in scope, {internal} internal research "
        f"row(s); therapeutic areas: {tas_phrase}."
    )
    if pub_src:
        out += f" Publication sources: {pub_src}."
    if int_lbl:
        out += f" Internal research labels: {int_lbl}."
    return out


def humanize_scan_summary_line(line: str) -> str:
    """Turn FR28 compact telemetry into short plain-language sentences."""
    t = line.strip()
    if not t:
        return t

    clin = _humanize_clinical_scan_line(t)
    if clin is not None:
        return clin

    m = _COMPETITOR_RE.match(t)
    if m:
        appr, disc, pipe, patents, pipe_scopes, patent_comp = m.groups()
        out = (
            f"Competitor — regulatory approvals surfaced: {appr}; disclosures: {disc}; "
            f"pipeline disclosure items: {pipe}; patent flags: {patents}."
        )
        if pipe_scopes:
            out += f" Pipeline scopes: {pipe_scopes}."
        if patent_comp:
            out += f" Patent watch: {patent_comp}."
        return out

    m = _CONSUMER_RE.match(t)
    if m:
        pm, fb, sales, unmet, sales_scopes = m.groups()
        mode = "practice / demo data" if pm.lower() == "true" else "configured feeds"
        out = (
            f"Consumer — {mode}; feedback themes: {fb}; pharmacy sales rows: {sales}; "
            f"unmet-need / demand signals: {unmet}."
        )
        if sales_scopes:
            out += f" Sales scopes: {sales_scopes}."
        return out

    return t


def humanize_scan_summary_lines(lines: list[str]) -> list[str]:
    return [humanize_scan_summary_line(x) for x in lines]


@dataclass(frozen=True)
class RunSummaryReportParts:
    """Pre-rendered run-summary slices for Markdown, HTML, and DOCX."""

    humanized_scan_lines: list[str]
    coverage_gap_lines: list[str]
    operator_gap_lines: list[str]
    coverage_remaining: int
    operator_remaining: int


def prepare_run_summary_for_report(synthesis: SynthesisOutput) -> RunSummaryReportParts:
    """Humanized FR28 lines plus partitioned, formatted upstream gaps."""
    human = humanize_scan_summary_lines(synthesis.scan_summary_lines)
    sec = build_executive_gap_sections(synthesis)
    cov_fmt = [format_gap_line_for_report(x) for x in sec.coverage]
    op_fmt = [format_gap_line_for_report(x) for x in sec.operator]
    return RunSummaryReportParts(
        humanized_scan_lines=human,
        coverage_gap_lines=cov_fmt,
        operator_gap_lines=op_fmt,
        coverage_remaining=sec.coverage_remaining,
        operator_remaining=sec.operator_remaining,
    )
