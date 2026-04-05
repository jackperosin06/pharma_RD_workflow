"""Load internal research summaries from JSON files (FR7, NFR-I1)."""

from __future__ import annotations

import json
from pathlib import Path

from pharma_rd.config import Settings
from pharma_rd.pipeline.contracts import InternalResearchItem

# MVP: refuse very large files; surface in data_gaps instead of reading whole file.


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _parse_one_record(obj: object, source_hint: str) -> InternalResearchItem:
    if not isinstance(obj, dict):
        raise ValueError(f"expected object, got {type(obj).__name__}")
    title = obj.get("title")
    summary = obj.get("summary")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing or invalid title")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid summary")
    ref = obj.get("reference")
    ref_s = ref if isinstance(ref, str) and ref.strip() else source_hint
    label = obj.get("source_label")
    label_s = label if isinstance(label, str) and label.strip() else "internal"
    return InternalResearchItem(
        title=title.strip(),
        summary=summary.strip(),
        reference=ref_s.strip(),
        source_label=label_s.strip(),
    )


def _load_json_file(
    path: Path,
    *,
    max_bytes: int,
) -> tuple[list[InternalResearchItem], list[str]]:
    gaps: list[str] = []
    try:
        st = path.stat()
    except OSError as e:
        return [], [f"Internal research: cannot stat {path}: {e}"]
    if st.st_size > max_bytes:
        return [], [
            f"Internal research: skipped {path.name} (size {st.st_size} "
            f"exceeds max {max_bytes} bytes)."
        ]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [], [f"Internal research: cannot read {path}: {e}"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [], [f"Internal research: invalid JSON in {path.name}: {e}"]
    items: list[InternalResearchItem] = []
    hint = str(path)
    try:
        if isinstance(data, list):
            for i, el in enumerate(data):
                items.append(_parse_one_record(el, f"{hint}#{i}"))
        elif isinstance(data, dict):
            items.append(_parse_one_record(data, hint))
        else:
            return [], [
                f"Internal research: JSON root in {path.name} must be object or array."
            ]
    except ValueError as e:
        return [], [f"Internal research: {path.name}: {e}"]
    return items, gaps


def ingest_internal_research(
    settings: Settings,
) -> tuple[list[InternalResearchItem], list[str], list[str]]:
    """
    Load internal research items from configured path.

    Returns (items, integration_notes, data_gaps). Never raises for I/O or parse
    issues — gaps/notes carry NFR-I1 transparency.
    """
    raw = settings.internal_research_path
    if raw is None:
        return (
            [],
            [
                "Internal research ingestion: not configured "
                "(set PHARMA_RD_INTERNAL_RESEARCH_PATH to a JSON file or directory "
                "of *.json files)."
            ],
            [],
        )

    path = _resolve_config_path(str(raw))
    max_b = settings.internal_research_max_file_bytes
    items: list[InternalResearchItem] = []
    notes: list[str] = []
    gaps: list[str] = []

    if not path.exists():
        return [], [], [f"Internal research path does not exist: {path}"]

    if path.is_file():
        batch, g = _load_json_file(path, max_bytes=max_b)
        items.extend(batch)
        gaps.extend(g)
        if batch:
            notes.append(
                f"Internal research: loaded {len(batch)} record(s) from {path.name}."
            )
        return items, notes, gaps

    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        if not json_files:
            gaps.append(
                f"Internal research directory {path} contains no *.json files."
            )
            return [], [], gaps
        for jp in json_files:
            batch, g = _load_json_file(jp, max_bytes=max_b)
            items.extend(batch)
            gaps.extend(g)
        if items:
            notes.append(
                f"Internal research: loaded {len(items)} record(s) from "
                f"{len(json_files)} file(s) under {path.name}/."
            )
        return items, notes, gaps

    gaps.append(f"Internal research path is not a file or directory: {path}")
    return [], [], gaps
