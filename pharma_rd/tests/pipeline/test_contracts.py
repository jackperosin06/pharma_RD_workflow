"""Round-trip tests for Pydantic stage contracts."""

from __future__ import annotations

from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerOutput,
    DeliveryOutput,
    SynthesisOutput,
)


def test_contracts_json_roundtrip() -> None:
    models = [
        ClinicalOutput(),
        CompetitorOutput(),
        ConsumerOutput(),
        SynthesisOutput(),
        DeliveryOutput(),
    ]
    for m in models:
        js = m.model_dump_json()
        assert "schema_version" in js
        assert m.__class__.model_validate_json(js) == m
