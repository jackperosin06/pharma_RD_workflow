"""Validate insight ``report.md`` for UTF-8 and stable structure (Epic 7.3)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

# Headings emitted by ``pharma_rd.agents.delivery._render_markdown`` — keep in sync.
_MARKDOWN_SECTION_MARKERS = (
    "## Run summary",
    "## Ranked opportunities",
    "## Governance and disclaimer",
)


def validate_readable_insight_report(
    path: Path,
    *,
    required_content_snippets: Sequence[str] | None = None,
) -> None:
    """Raise ``ValueError`` if ``path`` is not a readable UTF-8 insight report.

    Checks structural markers so CI can prove summary / rankings / governance are
    present. Optional ``required_content_snippets`` (e.g. opportunity title) tie the
    file to a specific synthesis fixture.
    """
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"not valid UTF-8: {path}") from e

    for marker in _MARKDOWN_SECTION_MARKERS:
        if marker not in text:
            raise ValueError(f"missing structural marker {marker!r} in {path}")

    if required_content_snippets:
        for s in required_content_snippets:
            if s not in text:
                raise ValueError(f"missing expected content {s!r} in {path}")
