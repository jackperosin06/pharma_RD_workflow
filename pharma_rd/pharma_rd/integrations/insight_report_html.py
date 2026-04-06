"""Rich HTML shell for insight reports (template + GPT fragment wrapper)."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from pharma_rd.config import Settings
from pharma_rd.integrations.report_executive_framing import prepare_run_summary_for_report
from pharma_rd.pipeline.contracts import SynthesisOutput

# Shared typography / layout for browser and PDF (WeasyPrint).
INSIGHT_REPORT_CSS = """
:root {
  --ink: #0f172a;
  --muted: #475569;
  --line: #e2e8f0;
  --surface: #f8fafc;
  --card: #ffffff;
  --accent: #0d9488;
  --accent-soft: #ccfbf1;
  --warn: #b45309;
  --radius: 12px;
  --shadow: 0 4px 24px rgba(15, 23, 42, 0.08);
  --font: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}
@page {
  size: A4;
  margin: 14mm 16mm;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--font);
  color: var(--ink);
  background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 320px, #f8fafc 100%);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.report-wrap {
  max-width: 52rem;
  margin: 0 auto;
  padding: 2rem 1.25rem 3rem;
}
.report-hero {
  background: linear-gradient(135deg, #0f766e 0%, #0d9488 42%, #14b8a6 100%);
  color: #f0fdfa;
  border-radius: var(--radius);
  padding: 1.75rem 1.75rem 1.5rem;
  box-shadow: var(--shadow);
  margin-bottom: 1.75rem;
}
.report-hero h1 {
  margin: 0 0 0.35rem;
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.report-hero .sub {
  opacity: 0.92;
  font-size: 0.95rem;
}
.report-hero .meta {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  font-size: 0.88rem;
  opacity: 0.95;
}
.badge {
  display: inline-block;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.35);
}
.card {
  background: var(--card);
  border-radius: var(--radius);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  padding: 1.35rem 1.5rem;
  margin-bottom: 1.25rem;
}
.card h2 {
  margin: 0 0 1rem;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--ink);
  padding-bottom: 0.65rem;
  border-bottom: 2px solid var(--accent-soft);
}
.fr22-banner {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.92rem;
  color: #78350f;
}
.fr26-banner {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: #1e3a5f;
}
.scan-grid {
  display: grid;
  gap: 0.65rem;
}
.scan-row {
  padding: 0.55rem 0.75rem;
  background: var(--surface);
  border-radius: 8px;
  border-left: 3px solid var(--accent);
  font-size: 0.9rem;
}
.gaps-list {
  margin: 0;
  padding-left: 1.15rem;
  color: var(--muted);
  font-size: 0.88rem;
}
.gaps-list li { margin: 0.35rem 0; }
.opp-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  margin-bottom: 1.25rem;
  background: var(--card);
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
}
.opp-head {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem 1.15rem;
  background: linear-gradient(90deg, var(--accent-soft) 0%, #fff 48%);
  border-bottom: 1px solid var(--line);
}
.rank-pill {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  font-weight: 800;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.opp-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.35;
}
.opp-body { padding: 1rem 1.15rem 1.15rem; }
.opp-note {
  font-size: 0.88rem;
  color: var(--muted);
  font-style: italic;
  margin: 0 0 0.85rem;
}
.label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  margin: 0.75rem 0 0.35rem;
}
.label:first-child { margin-top: 0; }
.muted-note {
  font-size: 0.88rem;
  color: var(--muted);
  margin: 0 0 0.5rem;
}
.prose {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.92rem;
  line-height: 1.55;
  background: var(--surface);
  padding: 0.75rem 0.9rem;
  border-radius: 8px;
  border: 1px solid var(--line);
}
.evidence-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.evidence-list li {
  padding: 0.45rem 0.6rem;
  margin-bottom: 0.35rem;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 0.88rem;
  border: 1px solid var(--line);
}
.report-footer {
  margin-top: 2rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--line);
  font-size: 0.85rem;
  color: var(--muted);
}
.report-footer p { margin: 0.5rem 0; }
.gpt-body { font-size: 0.95rem; }
.gpt-body h1, .gpt-body h2, .gpt-body h3 { color: var(--ink); }
.gpt-body a { color: var(--accent); }
@media print {
  body { background: #fff; }
  .report-wrap { padding: 0; max-width: none; }
  .report-hero { break-inside: avoid; }
  .opp-card { break-inside: avoid; }
}
"""


def _generated_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _document_shell(
    *,
    title: str,
    run_id: str,
    settings: Settings,
    fr26_html: str,
    inner_body: str,
) -> str:
    org = escape((settings.insight_org_display_name or "").strip() or "Organization")
    rid = escape(run_id)
    stamp = escape(_generated_stamp())
    parts: list[str] = [
        "<!DOCTYPE html>\n",
        '<html lang="en">\n<head>\n',
        '<meta charset="utf-8" />\n',
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n',
        f"<title>{escape(title)}</title>\n",
        "<style>\n",
        INSIGHT_REPORT_CSS,
        "</style>\n</head>\n<body>\n",
        '<div class="report-wrap">\n',
        '<header class="report-hero">\n',
        f'<p class="sub">{org} · Insight intelligence</p>\n',
        f"<h1>{escape(title)}</h1>\n",
        '<div class="meta">\n',
        f'<span><strong>Run</strong> · <code style="background:rgba(0,0,0,.12);'
        f'padding:0.1rem 0.35rem;border-radius:4px">{rid}</code></span>\n',
        f"<span><strong>Generated</strong> · {stamp}</span>\n",
        "</div>\n",
        "</header>\n",
        inner_body,
        fr26_html,
        "</div>\n</body>\n</html>\n",
    ]
    return "".join(parts)


def build_insight_report_html(
    run_id: str,
    syn: SynthesisOutput,
    settings: Settings,
    fr26_html: str,
) -> str:
    """Full HTML report for the template renderer path."""
    parts_body: list[str] = []
    parts_body.append(
        '<section class="card" aria-labelledby="run-summary">\n'
        '<h2 id="run-summary">Run summary</h2>\n'
        '<div class="fr22-banner" role="note">\n'
        "<p><strong>Human judgment (FR22):</strong> Items in this report are "
        "<strong>recommendations</strong> for review only—not "
        "<strong>approvals</strong>. "
        "<strong>Pursuit and portfolio decisions remain human-owned.</strong></p>\n"
        "</div>\n"
    )
    if fr26_html.strip():
        parts_body.append(f'<div class="fr26-banner">{fr26_html}</div>\n')
    rsum = prepare_run_summary_for_report(syn)
    sig = escape(str(syn.signal_characterization))
    parts_body.append(
        f'<p><span class="badge">Signal · {sig}</span></p>\n'
        '<div class="label">Monitoring snapshot (FR28)</div>\n'
        '<div class="scan-grid">\n'
    )
    if rsum.humanized_scan_lines:
        for line in rsum.humanized_scan_lines:
            parts_body.append(f'<div class="scan-row">{escape(line)}</div>\n')
    else:
        parts_body.append(
            '<div class="scan-row"><em>(No scan summary lines — legacy or empty '
            "synthesis.)</em></div>\n"
        )
    parts_body.append("</div>\n")
    if rsum.coverage_gap_lines:
        parts_body.append(
            '<div class="label">Coverage and configuration gaps (preview)</div>\n'
            '<ul class="gaps-list">\n'
        )
        for g in rsum.coverage_gap_lines:
            parts_body.append(f"<li>{escape(g)}</li>\n")
        if rsum.coverage_remaining:
            parts_body.append(
                f"<li>… ({rsum.coverage_remaining} more)</li>\n"
            )
        parts_body.append("</ul>\n")
    if rsum.operator_gap_lines:
        parts_body.append(
            '<div class="label">Technical pipeline notes (operators)</div>\n'
            '<p class="muted-note"><em>Internal telemetry for this run; JSON '
            "artifacts hold full detail.</em></p>\n"
            '<ul class="gaps-list">\n'
        )
        for g in rsum.operator_gap_lines:
            parts_body.append(f"<li>{escape(g)}</li>\n")
        if rsum.operator_remaining:
            parts_body.append(
                f"<li>… ({rsum.operator_remaining} more)</li>\n"
            )
        parts_body.append("</ul>\n")
    parts_body.append("</section>\n")

    parts_body.append(
        '<section class="card" aria-labelledby="ranked">\n'
        '<h2 id="ranked">Ranked opportunities</h2>\n'
    )
    if not syn.ranked_opportunities:
        parts_body.append("<p><em>(none)</em></p>\n")
    else:
        for row in sorted(syn.ranked_opportunities, key=lambda r: r.rank):
            parts_body.append('<article class="opp-card">\n<div class="opp-head">\n')
            parts_body.append(
                f'<div class="rank-pill" aria-hidden="true">{escape(str(row.rank))}'
                "</div>\n"
            )
            parts_body.append(
                f'<h3 class="opp-title">{escape(str(row.rank))}. {escape(row.title)}'
                "</h3>\n</div>\n"
            )
            parts_body.append('<div class="opp-body">\n')
            parts_body.append(
                '<p class="opp-note">Recommendation only—not an approval. '
                "Pursuit is a human decision.</p>\n"
            )
            parts_body.append('<div class="label">Rationale</div>\n')
            parts_body.append(f'<p class="prose">{escape(row.rationale_short)}</p>\n')
            if row.evidence_references:
                parts_body.append('<div class="label">Evidence references</div>\n')
                parts_body.append('<ul class="evidence-list">\n')
                for er in row.evidence_references:
                    parts_body.append(
                        "<li><strong>"
                        + escape(er.domain)
                        + "</strong> — "
                        + escape(er.label)
                        + ": "
                        + escape(er.reference)
                        + "</li>\n"
                    )
                parts_body.append("</ul>\n")
            parts_body.append('<div class="label">Commercial viability</div>\n')
            parts_body.append(
                f'<p class="prose">{escape(row.commercial_viability)}</p>\n'
            )
            parts_body.append("</div>\n</article>\n")
    parts_body.append("</section>\n")

    gov = (
        "This report presents recommendations derived from signals available to the "
        "workflow. It does not approve development, launch, or commercialization. "
        "Pursuit decisions remain with qualified human decision-makers and your "
        "organization's governance processes."
    )
    foot = (
        "Recommendations, not approvals—pursuit decisions remain human-owned (FR22)."
    )
    parts_body.append(
        '<section class="card" aria-labelledby="gov">\n'
        f'<h2 id="gov">Governance and disclaimer</h2>\n'
        f"<p>{escape(gov)}</p>\n"
        '<footer class="report-footer">\n'
        f"<p>{escape(foot)}</p>\n"
        "</footer>\n</section>\n"
    )

    title = f"Insight report ({run_id})"
    return _document_shell(
        title=title,
        run_id=run_id,
        settings=settings,
        fr26_html="",
        inner_body="".join(parts_body),
    )


def wrap_gpt_body_as_document(
    run_id: str,
    inner_html: str,
    settings: Settings,
    fr26_html: str,
) -> str:
    """Trusted shell around sanitized GPT HTML body (same visual system)."""
    inner = (
        '<main class="card gpt-shell"><h2 class="sr-only">Report narrative</h2>\n'
        f'<div class="gpt-body">{inner_html}</div>\n</main>\n'
    )
    # Screen-reader only heading; keep layout clean.
    css_extra = (
        ".sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;"
        "overflow:hidden;clip:rect(0,0,0,0);border:0;}\n"
    )
    title = f"Insight report ({run_id})"
    org = escape((settings.insight_org_display_name or "").strip() or "Organization")
    rid = escape(run_id)
    stamp = escape(_generated_stamp())
    parts: list[str] = [
        "<!DOCTYPE html>\n",
        '<html lang="en">\n<head>\n',
        '<meta charset="utf-8" />\n',
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n',
        f"<title>{escape(title)}</title>\n",
        "<style>\n",
        INSIGHT_REPORT_CSS,
        css_extra,
        "</style>\n</head>\n<body>\n",
        '<div class="report-wrap">\n',
        '<header class="report-hero">\n',
        f'<p class="sub">{org} · Insight intelligence</p>\n',
        f"<h1>{escape(title)}</h1>\n",
        '<div class="meta">\n',
        f'<span><strong>Run</strong> · <code style="background:rgba(0,0,0,.12);'
        f'padding:0.1rem 0.35rem;border-radius:4px">{rid}</code></span>\n',
        f"<span><strong>Generated</strong> · {stamp}</span>\n",
        "</div>\n",
        "</header>\n",
        inner,
        fr26_html,
        "</div>\n</body>\n</html>\n",
    ]
    return "".join(parts)
