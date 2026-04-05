"""Pydantic handoff contracts between pipeline stages (snake_case JSON)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PublicationItem(BaseModel):
    """One publication or trial-linked summary surfaced by the Clinical agent."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    reference: str
    source: str = "pubmed"


class InternalResearchItem(BaseModel):
    """One internal research summary loaded from configured JSON (FR7)."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    reference: str
    source_label: str = "internal"


class ClinicalOutput(BaseModel):
    """Structured output for the clinical stage (schema_version 2 — Epic 3)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 2
    run_id: str
    therapeutic_areas_configured: list[str] = Field(default_factory=list)
    publication_items: list[PublicationItem] = Field(default_factory=list)
    internal_research_items: list[InternalResearchItem] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    integration_notes: list[str] = Field(default_factory=list)


class RegulatoryApprovalItem(BaseModel):
    """One approval-like regulatory signal (FR8)."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    reference: str
    source_label: str = "openfda"
    observed_at: str


class RegulatoryDisclosureItem(BaseModel):
    """One material regulatory disclosure signal (FR8)."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    reference: str
    source_label: str = "fixture"
    observed_at: str


class PipelineDisclosureItem(BaseModel):
    """One pipeline-oriented disclosure signal scoped by watch configuration (FR9)."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    reference: str
    source_label: str = "fixture"
    observed_at: str
    matched_scope: str


class PatentFilingFlagItem(BaseModel):
    """One patent-related competitive signal (FR10)."""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    reference: str
    source_label: str = "fixture"
    observed_at: str
    matched_competitor: str


class CompetitorOutput(BaseModel):
    """Structured output for the competitor stage (schema_version 4 — Epic 4 / FR10)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 4
    run_id: str
    approval_items: list[RegulatoryApprovalItem] = Field(default_factory=list)
    disclosure_items: list[RegulatoryDisclosureItem] = Field(default_factory=list)
    pipeline_disclosure_items: list[PipelineDisclosureItem] = Field(
        default_factory=list
    )
    patent_filing_flags: list[PatentFilingFlagItem] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    integration_notes: list[str] = Field(default_factory=list)


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
