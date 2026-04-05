"""Pharmacy sales trend fixtures (FR12, NFR-I1)."""

from __future__ import annotations

import json
from pathlib import Path

from pharma_rd.config import Settings
from pharma_rd.pipeline.contracts import PharmacySalesTrendItem


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _parse_trend_obj(obj: object, hint: str) -> PharmacySalesTrendItem:
    if not isinstance(obj, dict):
        raise ValueError(f"sales trend must be object, got {type(obj).__name__}")
    summary = obj.get("summary")
    scope = obj.get("scope")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid summary")
    if not isinstance(scope, str) or not scope.strip():
        raise ValueError("missing or invalid scope")
    period = obj.get("period")
    period_s: str | None
    if period is None:
        period_s = None
    elif isinstance(period, bool):
        period_s = None
    elif isinstance(period, str) and period.strip():
        period_s = period.strip()
    elif isinstance(period, (int, float)):
        period_s = str(period)
    else:
        period_s = None
    src = obj.get("source")
    src_s = src if isinstance(src, str) and src.strip() else hint
    return PharmacySalesTrendItem(
        summary=summary.strip(),
        scope=scope.strip(),
        period=period_s,
        source=src_s.strip(),
    )


def _load_one_fixture_file(
    path: Path,
    *,
    max_bytes: int,
) -> tuple[list[PharmacySalesTrendItem], list[str]]:
    """Return (trends, data_gaps). Never raises."""
    gaps: list[str] = []
    try:
        size = path.stat().st_size
    except OSError as e:
        gaps.append(f"Pharmacy sales: cannot stat {path}: {e}")
        return [], gaps
    if size > max_bytes:
        gaps.append(
            f"Pharmacy sales: file {path.name} exceeds max bytes "
            f"({size} > {max_bytes})."
        )
        return [], gaps
    try:
        raw = path.read_bytes()
    except OSError as e:
        gaps.append(f"Pharmacy sales: cannot read {path}: {e}")
        return [], gaps
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        gaps.append(f"Pharmacy sales: invalid JSON in {path.name}: {e}")
        return [], gaps
    if not isinstance(data, dict):
        gaps.append(
            f"Pharmacy sales: root of {path.name} must be a JSON object (NFR-I1)."
        )
        return [], gaps
    raw_trends = data.get("pharmacy_sales_trends")
    if raw_trends is None:
        gaps.append(
            f"Pharmacy sales: {path.name} has missing or null `pharmacy_sales_trends` "
            "(expected a JSON array; NFR-I1)."
        )
        return [], gaps
    if not isinstance(raw_trends, list):
        gaps.append(
            f"Pharmacy sales: pharmacy_sales_trends must be an array in {path.name}."
        )
        return [], gaps
    trends: list[PharmacySalesTrendItem] = []
    hint = f"fixture:{path.name}"
    for i, item in enumerate(raw_trends):
        try:
            trends.append(_parse_trend_obj(item, hint))
        except ValueError as e:
            gaps.append(
                f"Pharmacy sales: pharmacy_sales_trends[{i}] in {path.name}: {e}"
            )
    return trends, gaps


def ingest_pharmacy_sales_fixture(
    settings: Settings,
) -> tuple[list[PharmacySalesTrendItem], list[str], list[str]]:
    """
    Load pharmacy_sales_trends from configured JSON path.

    Returns (trends, integration_notes, data_gaps). Never raises.
    """
    raw = settings.pharmacy_sales_path
    if raw is None:
        return [], [], []

    path = _resolve_config_path(str(raw))
    max_b = settings.pharmacy_sales_max_file_bytes
    notes: list[str] = []
    gaps: list[str] = []

    if not path.exists():
        msg = f"Pharmacy sales path does not exist: {path}"
        return [], [], [msg]

    if path.is_file():
        trends, g = _load_one_fixture_file(path, max_bytes=max_b)
        gaps.extend(g)
        if trends:
            notes.append(
                f"Pharmacy sales (FR12): loaded {len(trends)} trend(s) from "
                f"fixture {path.name}."
            )
        elif not g:
            notes.append(
                f"Pharmacy sales (FR12): fixture {path.name} returned no trends "
                "(empty array; NFR-I1)."
            )
        return trends, notes, gaps

    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        if not json_files:
            gaps.append(f"Pharmacy sales directory {path} contains no *.json files.")
            return [], [], gaps
        all_trends: list[PharmacySalesTrendItem] = []
        for jp in json_files:
            t, g = _load_one_fixture_file(jp, max_bytes=max_b)
            all_trends.extend(t)
            gaps.extend(g)
        if all_trends:
            notes.append(
                f"Pharmacy sales (FR12): loaded {len(all_trends)} trend(s) from "
                f"{len(json_files)} file(s) under {path.name}/."
            )
        elif not gaps:
            notes.append(
                "Pharmacy sales (FR12): configured directory produced no trends "
                "(NFR-I1)."
            )
        return all_trends, notes, gaps

    gaps.append(f"Pharmacy sales path is not a file or directory: {path}")
    return [], [], gaps
