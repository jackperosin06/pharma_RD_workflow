"""Insight report readability validation (Epic 7.3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pharma_rd.readability import validate_readable_insight_report


def test_validate_accepts_well_formed_md(tmp_path: Path) -> None:
    p = tmp_path / "report.md"
    p.write_text(
        "# x\n## Run summary\n.\n## Ranked opportunities\n(none)\n"
        "## Governance and disclaimer\nok\n",
        encoding="utf-8",
    )
    validate_readable_insight_report(p)


def test_validate_readable_insight_report_requires_markers(tmp_path: Path) -> None:
    p = tmp_path / "bad.md"
    p.write_text("# only a title\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Run summary"):
        validate_readable_insight_report(p)


def test_validate_readable_insight_report_requires_utf8(tmp_path: Path) -> None:
    p = tmp_path / "latin1.md"
    p.write_bytes(b"\xff\xfe## Run summary\n")
    with pytest.raises(ValueError, match="UTF-8"):
        validate_readable_insight_report(p)


def test_validate_readable_insight_report_optional_snippets(tmp_path: Path) -> None:
    p = tmp_path / "report.md"
    p.write_text(
        "## Run summary\nx\n## Ranked opportunities\n(none)\n"
        "## Governance and disclaimer\nz\n",
        encoding="utf-8",
    )
    validate_readable_insight_report(p, required_content_snippets=("x",))
    with pytest.raises(ValueError, match="missing expected"):
        validate_readable_insight_report(p, required_content_snippets=("not-there",))
