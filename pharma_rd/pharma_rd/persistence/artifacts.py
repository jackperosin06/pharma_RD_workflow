"""Filesystem artifact blobs + SQLite metadata for stage outputs."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError


def artifact_relative_path(run_id: str, stage_key: str) -> str:
    """Stable relative path under the artifact root (POSIX-style segments)."""
    return f"{run_id}/{stage_key}/output.json"


def read_artifact_bytes(artifact_root: Path, run_id: str, stage_key: str) -> bytes:
    """Read raw JSON bytes for a completed stage (runner handoff)."""
    path = artifact_root / run_id / stage_key / "output.json"
    return path.read_bytes()


def read_stage_artifact_model[T: BaseModel](
    artifact_root: Path,
    run_id: str,
    stage_key: str,
    model_cls: type[T],
) -> T:
    """Read ``output.json`` for a stage and validate with ``model_cls`` (FR14).

    Raises ``FileNotFoundError`` with an operator-oriented message if the file is
    missing; ``OSError`` if unreadable; ``ValueError`` if JSON is invalid for the model.
    """
    path = artifact_root / run_id / stage_key / "output.json"
    try:
        raw = path.read_bytes()
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Missing required artifact: run_id={run_id!r} stage={stage_key!r} "
            f"path={path}"
        ) from e
    except OSError as e:
        raise OSError(
            f"Cannot read artifact: run_id={run_id!r} stage={stage_key!r} "
            f"path={path}: {e}"
        ) from e
    try:
        return model_cls.model_validate_json(raw)
    except ValidationError as e:
        raise ValueError(
            f"Artifact validation failed for run_id={run_id!r} stage={stage_key!r} "
            f"path={path}: {e}"
        ) from e


@dataclass(frozen=True)
class StageArtifactRecord:
    """Row-shaped result after persisting a stage artifact."""

    run_id: str
    stage_key: str
    relative_path: str
    sha256_hex: str
    byte_size: int
    created_at: str


def write_stage_artifact(
    conn: sqlite3.Connection,
    *,
    artifact_root: Path,
    run_id: str,
    stage_key: str,
    model: BaseModel,
) -> StageArtifactRecord:
    """Serialize model to JSON, write atomically under artifact_root, store metadata.

    Layout: ``{artifact_root}/{run_id}/{stage_key}/output.json`` (see README).
    Writes ``output.json.tmp`` then renames to ``output.json`` in that folder.
    """
    rel = artifact_relative_path(run_id, stage_key)
    out_dir = artifact_root / run_id / stage_key
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / "output.json"
    tmp_path = out_dir / "output.json.tmp"

    payload = model.model_dump_json().encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    now = datetime.now(UTC).isoformat()

    tmp_path.write_bytes(payload)
    tmp_path.replace(final_path)

    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO stage_artifacts (
                run_id, stage_key, relative_path, sha256_hex, byte_size, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, stage_key, rel, digest, len(payload), now),
        )
        conn.commit()
    except Exception:
        if final_path.is_file():
            final_path.unlink()
        raise
    return StageArtifactRecord(
        run_id=run_id,
        stage_key=stage_key,
        relative_path=rel,
        sha256_hex=digest,
        byte_size=len(payload),
        created_at=now,
    )


def write_utf8_artifact_atomic(
    artifact_root: Path,
    relative_segments: tuple[str, ...],
    text: str,
) -> tuple[str, int]:
    """Write UTF-8 text using ``.tmp`` then rename (same safety as ``output.json``).

    Returns ``(posix-style relative path, byte length)``.
    """
    rel = "/".join(relative_segments)
    out_dir = artifact_root.joinpath(*relative_segments[:-1])
    out_dir.mkdir(parents=True, exist_ok=True)
    final_name = relative_segments[-1]
    final_path = out_dir / final_name
    tmp_path = out_dir / f"{final_name}.tmp"
    payload = text.encode("utf-8")
    tmp_path.write_bytes(payload)
    tmp_path.replace(final_path)
    return rel, len(payload)
