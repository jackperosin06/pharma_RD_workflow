"""Filesystem artifact blobs + SQLite metadata for stage outputs."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


def artifact_relative_path(run_id: str, stage_key: str) -> str:
    """Stable relative path under the artifact root (POSIX-style segments)."""
    return f"{run_id}/{stage_key}/output.json"


def read_artifact_bytes(artifact_root: Path, run_id: str, stage_key: str) -> bytes:
    """Read raw JSON bytes for a completed stage (runner handoff)."""
    path = artifact_root / run_id / stage_key / "output.json"
    return path.read_bytes()


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
