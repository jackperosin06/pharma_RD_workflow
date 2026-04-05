"""Stage artifact JSON validation (FR14)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pharma_rd.persistence.artifacts import read_stage_artifact_model
from pharma_rd.pipeline.contracts import ClinicalOutput


def test_read_stage_artifact_model_missing(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    with pytest.raises(FileNotFoundError, match="Missing required artifact"):
        read_stage_artifact_model(root, "run-x", "clinical", ClinicalOutput)


def test_read_stage_artifact_model_invalid_json(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    p = root / "run-x" / "clinical" / "output.json"
    p.parent.mkdir(parents=True)
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Artifact validation failed"):
        read_stage_artifact_model(root, "run-x", "clinical", ClinicalOutput)


def test_read_stage_artifact_model_garbled_bytes(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    p = root / "run-x" / "clinical" / "output.json"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ValueError, match="Artifact validation failed"):
        read_stage_artifact_model(root, "run-x", "clinical", ClinicalOutput)


def test_read_stage_artifact_model_ok(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    p = root / "run-x" / "clinical" / "output.json"
    p.parent.mkdir(parents=True)
    p.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "run_id": "run-x",
                "therapeutic_areas_configured": [],
                "publication_items": [],
                "internal_research_items": [],
                "data_gaps": [],
                "integration_notes": [],
            }
        ),
        encoding="utf-8",
    )
    m = read_stage_artifact_model(root, "run-x", "clinical", ClinicalOutput)
    assert m.run_id == "run-x"
