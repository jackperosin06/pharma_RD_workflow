"""Consumer feedback themes: JSON fixtures (FR11, NFR-I1)."""

from __future__ import annotations

import json
from pathlib import Path

from pharma_rd.config import Settings
from pharma_rd.pipeline.contracts import ConsumerFeedbackThemeItem


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _parse_theme_obj(obj: object, hint: str) -> ConsumerFeedbackThemeItem:
    if not isinstance(obj, dict):
        raise ValueError(f"feedback theme must be object, got {type(obj).__name__}")
    theme = obj.get("theme")
    summary = obj.get("summary")
    if not isinstance(theme, str) or not theme.strip():
        raise ValueError("missing or invalid theme")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid summary")
    src = obj.get("source")
    src_s = src if isinstance(src, str) and src.strip() else hint
    return ConsumerFeedbackThemeItem(
        theme=theme.strip(),
        summary=summary.strip(),
        source=src_s.strip(),
    )


def _load_one_fixture_file(
    path: Path,
    *,
    max_bytes: int,
) -> tuple[list[ConsumerFeedbackThemeItem], list[str]]:
    """Return (themes, data_gaps). Never raises."""
    gaps: list[str] = []
    try:
        size = path.stat().st_size
    except OSError as e:
        gaps.append(f"Consumer feedback: cannot stat {path}: {e}")
        return [], gaps
    if size > max_bytes:
        gaps.append(
            f"Consumer feedback: file {path.name} exceeds max bytes "
            f"({size} > {max_bytes})."
        )
        return [], gaps
    try:
        raw = path.read_bytes()
    except OSError as e:
        gaps.append(f"Consumer feedback: cannot read {path}: {e}")
        return [], gaps
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        gaps.append(f"Consumer feedback: invalid JSON in {path.name}: {e}")
        return [], gaps
    if not isinstance(data, dict):
        gaps.append(
            f"Consumer feedback: root of {path.name} must be a JSON object (NFR-I1)."
        )
        return [], gaps
    raw_themes = data.get("feedback_themes")
    if raw_themes is None:
        gaps.append(
            f"Consumer feedback: {path.name} has missing or null `feedback_themes` "
            "(expected a JSON array; NFR-I1)."
        )
        return [], gaps
    if not isinstance(raw_themes, list):
        gaps.append(
            f"Consumer feedback: feedback_themes must be an array in {path.name}."
        )
        return [], gaps
    themes: list[ConsumerFeedbackThemeItem] = []
    hint = f"fixture:{path.name}"
    for i, item in enumerate(raw_themes):
        try:
            themes.append(_parse_theme_obj(item, hint))
        except ValueError as e:
            gaps.append(f"Consumer feedback: feedback_themes[{i}] in {path.name}: {e}")
    return themes, gaps


def ingest_consumer_feedback_fixture(
    settings: Settings,
) -> tuple[list[ConsumerFeedbackThemeItem], list[str], list[str]]:
    """
    Load feedback_themes from configured JSON path.

    Returns (themes, integration_notes, data_gaps). Never raises.
    """
    raw = settings.consumer_feedback_path
    if raw is None:
        return [], [], []

    path = _resolve_config_path(str(raw))
    max_b = settings.consumer_feedback_max_file_bytes
    notes: list[str] = []
    gaps: list[str] = []

    if not path.exists():
        msg = f"Consumer feedback path does not exist: {path}"
        return [], [], [msg]

    if path.is_file():
        themes, g = _load_one_fixture_file(path, max_bytes=max_b)
        gaps.extend(g)
        if themes:
            notes.append(
                f"Consumer feedback: loaded {len(themes)} theme(s) from "
                f"fixture {path.name} (FR11)."
            )
        return themes, notes, gaps

    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        if not json_files:
            gaps.append(f"Consumer feedback directory {path} contains no *.json files.")
            return [], [], gaps
        all_themes: list[ConsumerFeedbackThemeItem] = []
        for jp in json_files:
            t, g = _load_one_fixture_file(jp, max_bytes=max_b)
            all_themes.extend(t)
            gaps.extend(g)
        if all_themes:
            notes.append(
                f"Consumer feedback: loaded {len(all_themes)} theme(s) from "
                f"{len(json_files)} file(s) under {path.name}/ (FR11)."
            )
        return all_themes, notes, gaps

    gaps.append(f"Consumer feedback path is not a file or directory: {path}")
    return [], [], gaps
