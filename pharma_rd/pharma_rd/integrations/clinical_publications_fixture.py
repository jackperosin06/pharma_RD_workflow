"""Load clinical publication rows from JSON fixtures (demo / practice; FR6)."""

from __future__ import annotations

import json
from pathlib import Path

from pharma_rd.config import Settings
from pharma_rd.pipeline.contracts import PublicationItem


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _parse_one_record(obj: object) -> PublicationItem:
    if not isinstance(obj, dict):
        raise ValueError(f"expected object, got {type(obj).__name__}")
    title = obj.get("title")
    summary = obj.get("summary")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing or invalid title")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid summary")
    ref = obj.get("reference")
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("missing or invalid reference")
    src = obj.get("source")
    src_s = src if isinstance(src, str) and src.strip() else "pubmed"
    return PublicationItem(
        title=title.strip(),
        summary=summary.strip(),
        reference=ref.strip(),
        source=src_s.strip(),
    )


def _extract_publication_list(data: object) -> list[object]:
    if isinstance(data, list):
        return list(data)
    if isinstance(data, dict):
        pub = data.get("publications")
        if isinstance(pub, list):
            return list(pub)
    raise ValueError(
        'JSON root must be an array or an object with a "publications" array'
    )


def _load_json_file(
    path: Path,
    *,
    max_bytes: int,
) -> tuple[list[PublicationItem], list[str]]:
    gaps: list[str] = []
    try:
        st = path.stat()
    except OSError as e:
        return [], [f"Clinical publication fixture: cannot stat {path}: {e}"]
    if st.st_size > max_bytes:
        return [], [
            f"Clinical publication fixture: skipped {path.name} (size {st.st_size} "
            f"exceeds max {max_bytes} bytes)."
        ]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [], [f"Clinical publication fixture: cannot read {path}: {e}"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [], [f"Clinical publication fixture: invalid JSON in {path.name}: {e}"]
    items: list[PublicationItem] = []
    try:
        raw_list = _extract_publication_list(data)
        for el in raw_list:
            items.append(_parse_one_record(el))
    except ValueError as e:
        return [], [f"Clinical publication fixture: {path.name}: {e}"]
    return items, gaps


def ingest_clinical_publication_fixture(
    settings: Settings,
) -> tuple[list[PublicationItem], list[str], list[str]]:
    """
    Load ``PublicationItem`` rows from ``PHARMA_RD_CLINICAL_FIXTURE_PATH``.

    Returns (items, integration_notes, data_gaps). Never raises for I/O or parse
    issues — gaps/notes carry NFR-I1 transparency.
    """
    raw = settings.clinical_fixture_path
    if raw is None:
        return [], [], []

    path = _resolve_config_path(str(raw))
    max_b = settings.clinical_fixture_max_file_bytes
    notes: list[str] = []
    gaps: list[str] = []

    if not path.exists():
        return [], [], [f"Clinical publication fixture path does not exist: {path}"]

    if path.is_file():
        batch, g = _load_json_file(path, max_bytes=max_b)
        gaps.extend(g)
        if batch:
            notes.append(
                f"Clinical publication fixture: loaded {len(batch)} record(s) from "
                f"{path.name} (no live PubMed query)."
            )
        return batch, notes, gaps

    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        if not json_files:
            gaps.append(
                f"Clinical publication fixture directory {path} contains no "
                "*.json files."
            )
            return [], [], gaps
        items: list[PublicationItem] = []
        for jp in json_files:
            batch, g = _load_json_file(jp, max_bytes=max_b)
            items.extend(batch)
            gaps.extend(g)
        if items:
            notes.append(
                f"Clinical publication fixture: loaded {len(items)} record(s) from "
                f"{len(json_files)} file(s) under {path.name}/ (no live PubMed query)."
            )
        return items, notes, gaps

    gaps.append(f"Clinical publication fixture path is not a file or directory: {path}")
    return [], [], gaps
