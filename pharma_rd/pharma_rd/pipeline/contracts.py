"""Pydantic handoff contracts between pipeline stages (snake_case JSON)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ClinicalOutput(BaseModel):
    """Structured output for the clinical stage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    note: str = "stub"


class CompetitorOutput(BaseModel):
    """Structured output for the competitor intelligence stage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    note: str = "stub"


class ConsumerOutput(BaseModel):
    """Structured output for the consumer insight stage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    note: str = "stub"


class SynthesisOutput(BaseModel):
    """Structured output for the synthesis stage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    note: str = "stub"


class DeliveryOutput(BaseModel):
    """Structured output for the delivery stage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    note: str = "stub"
