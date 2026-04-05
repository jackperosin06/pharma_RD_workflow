"""Unmet need / demand market signals from JSON fixtures (FR13, NFR-I1)."""

from __future__ import annotations

import json
from pathlib import Path

from pharma_rd.config import Settings
from pharma_rd.pipeline.contracts import UnmetNeedDemandSignalItem


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def _parse_signal_obj(obj: object, hint: str) -> UnmetNeedDemandSignalItem:
    if not isinstance(obj, dict):
        raise ValueError(
            f"unmet need / demand signal must be object, got {type(obj).__name__}"
        )
    signal = obj.get("signal")
    summary = obj.get("summary")
    if not isinstance(signal, str) or not signal.strip():
        raise ValueError("missing or invalid signal")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("missing or invalid summary")
    src = obj.get("source")
    src_s = src if isinstance(src, str) and src.strip() else hint
    return UnmetNeedDemandSignalItem(
        signal=signal.strip(),
        summary=summary.strip(),
        source=src_s.strip(),
    )


def _load_one_fixture_file(
    path: Path,
    *,
    max_bytes: int,
) -> tuple[list[UnmetNeedDemandSignalItem], list[str]]:
    """Return (signals, data_gaps). Never raises."""
    gaps: list[str] = []
    try:
        size = path.stat().st_size
    except OSError as e:
        gaps.append(f"Unmet need / demand: cannot stat {path}: {e}")
        return [], gaps
    if size > max_bytes:
        gaps.append(
            f"Unmet need / demand: file {path.name} exceeds max bytes "
            f"({size} > {max_bytes})."
        )
        return [], gaps
    try:
        raw = path.read_bytes()
    except OSError as e:
        gaps.append(f"Unmet need / demand: cannot read {path}: {e}")
        return [], gaps
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        gaps.append(f"Unmet need / demand: invalid JSON in {path.name}: {e}")
        return [], gaps
    if not isinstance(data, dict):
        gaps.append(
            f"Unmet need / demand: root of {path.name} must be a JSON object (NFR-I1)."
        )
        return [], gaps
    raw_signals = data.get("unmet_need_demand_signals")
    if raw_signals is None:
        gaps.append(
            f"Unmet need / demand: {path.name} has missing or null "
            "`unmet_need_demand_signals` (expected a JSON array; NFR-I1)."
        )
        return [], gaps
    if not isinstance(raw_signals, list):
        gaps.append(
            f"Unmet need / demand: unmet_need_demand_signals must be an array in "
            f"{path.name}."
        )
        return [], gaps
    signals: list[UnmetNeedDemandSignalItem] = []
    hint = f"fixture:{path.name}"
    for i, item in enumerate(raw_signals):
        try:
            signals.append(_parse_signal_obj(item, hint))
        except ValueError as e:
            gaps.append(
                f"Unmet need / demand: unmet_need_demand_signals[{i}] in "
                f"{path.name}: {e}"
            )
    return signals, gaps


def ingest_unmet_need_demand_fixture(
    settings: Settings,
) -> tuple[list[UnmetNeedDemandSignalItem], list[str], list[str]]:
    """
    Load unmet_need_demand_signals from configured JSON path.

    Returns (signals, integration_notes, data_gaps). Never raises.
    """
    raw = settings.unmet_need_demand_path
    if raw is None:
        return [], [], []

    path = _resolve_config_path(str(raw))
    max_b = settings.unmet_need_demand_max_file_bytes
    notes: list[str] = []
    gaps: list[str] = []

    if not path.exists():
        msg = f"Unmet need / demand path does not exist: {path}"
        return [], [], [msg]

    if path.is_file():
        sigs, g = _load_one_fixture_file(path, max_bytes=max_b)
        gaps.extend(g)
        if sigs:
            notes.append(
                f"Unmet need / demand (FR13): loaded {len(sigs)} signal(s) from "
                f"fixture {path.name}."
            )
        elif not g:
            notes.append(
                f"Unmet need / demand (FR13): fixture {path.name} returned no signals "
                "(empty array; NFR-I1)."
            )
        return sigs, notes, gaps

    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        if not json_files:
            gaps.append(
                f"Unmet need / demand directory {path} contains no *.json files."
            )
            return [], [], gaps
        all_sigs: list[UnmetNeedDemandSignalItem] = []
        for jp in json_files:
            s, g = _load_one_fixture_file(jp, max_bytes=max_b)
            all_sigs.extend(s)
            gaps.extend(g)
        if all_sigs:
            notes.append(
                f"Unmet need / demand (FR13): loaded {len(all_sigs)} signal(s) from "
                f"{len(json_files)} file(s) under {path.name}/."
            )
        elif not gaps:
            notes.append(
                "Unmet need / demand (FR13): configured directory produced no "
                "signals (NFR-I1)."
            )
        return all_sigs, notes, gaps

    gaps.append(f"Unmet need / demand path is not a file or directory: {path}")
    return [], [], gaps
