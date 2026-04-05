"""Pydantic handoff contracts between pipeline stages (snake_case JSON)."""

from __future__ import annotations

from typing import Literal

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


class ClinicalGptAnalysis(BaseModel):
    """GPT-4o analyst layer for clinical publications (story 3.3 / FR6 extension)."""

    model_config = ConfigDict(extra="forbid")

    analyst_summary: str = ""
    ta_relevance_assessment: str = ""
    priority_trials_attention: list[str] = Field(default_factory=list)


class ClinicalOutput(BaseModel):
    """Structured output for the clinical stage (schema v3, Epic 3 + story 3.3)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 3
    run_id: str
    therapeutic_areas_configured: list[str] = Field(default_factory=list)
    publication_items: list[PublicationItem] = Field(default_factory=list)
    internal_research_items: list[InternalResearchItem] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    integration_notes: list[str] = Field(default_factory=list)
    clinical_gpt_analysis: ClinicalGptAnalysis | None = None


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


UrgentAttentionSeverity = Literal["none", "low", "medium", "high"]


class CompetitorGptAnalysis(BaseModel):
    """GPT-4o competitive intelligence layer (story 4.4 / FR8–FR10 extension)."""

    model_config = ConfigDict(extra="forbid")

    strategic_commentary: str = ""
    threat_opportunity_themes: list[str] = Field(default_factory=list)
    urgent_attention_flag: bool = False
    urgent_attention_items: list[str] = Field(default_factory=list)
    urgent_attention_severity: UrgentAttentionSeverity = "none"


class CompetitorOutput(BaseModel):
    """Structured output for the competitor stage (schema v5, Epic 4 + story 4.4)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 5
    run_id: str
    approval_items: list[RegulatoryApprovalItem] = Field(default_factory=list)
    disclosure_items: list[RegulatoryDisclosureItem] = Field(default_factory=list)
    pipeline_disclosure_items: list[PipelineDisclosureItem] = Field(
        default_factory=list
    )
    patent_filing_flags: list[PatentFilingFlagItem] = Field(default_factory=list)
    data_gaps: list[str] = Field(default_factory=list)
    integration_notes: list[str] = Field(default_factory=list)
    competitor_gpt_analysis: CompetitorGptAnalysis | None = None


class ConsumerFeedbackThemeItem(BaseModel):
    """One consumer feedback theme with a verifiable source reference (FR11)."""

    model_config = ConfigDict(extra="forbid")

    theme: str
    summary: str
    source: str


class PharmacySalesTrendItem(BaseModel):
    """One pharmacy sales trend line with explicit scope (FR12)."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    scope: str
    period: str | None = None
    source: str


class UnmetNeedDemandSignalItem(BaseModel):
    """One unmet-need / demand signal from market fixtures (FR13)."""

    model_config = ConfigDict(extra="forbid")

    signal: str
    summary: str
    source: str


class ConsumerGptAnalysis(BaseModel):
    """GPT-4o market analyst layer for consumer signals (story 5.4 / FR11–FR13)."""

    model_config = ConfigDict(extra="forbid")

    unmet_need_synthesis: str = ""
    demand_pattern_summary: str = ""
    line_extension_relevance: str = ""


class ConsumerOutput(BaseModel):
    """Structured output for the consumer insight stage (v5 — Epic 5 + story 5.4)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 5
    run_id: str
    feedback_themes: list[ConsumerFeedbackThemeItem] = Field(default_factory=list)
    pharmacy_sales_trends: list[PharmacySalesTrendItem] = Field(default_factory=list)
    unmet_need_demand_signals: list[UnmetNeedDemandSignalItem] = Field(
        default_factory=list
    )
    practice_mode: bool = True
    data_gaps: list[str] = Field(default_factory=list)
    integration_notes: list[str] = Field(default_factory=list)
    consumer_gpt_analysis: ConsumerGptAnalysis | None = None


class DomainCoverage(BaseModel):
    """Which monitoring domains contributed to one ranked row (FR15)."""

    model_config = ConfigDict(extra="forbid")

    clinical: bool
    competitor: bool
    consumer: bool


class EvidenceReferenceItem(BaseModel):
    """Verifiable evidence pointer for one domain (FR16)."""

    model_config = ConfigDict(extra="forbid")

    domain: Literal["clinical", "competitor", "consumer"]
    label: str
    reference: str


class RankedOpportunityItem(BaseModel):
    """One ranked line-extension opportunity (FR15–FR17)."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    title: str
    rationale_short: str
    domain_coverage: DomainCoverage
    evidence_references: list[EvidenceReferenceItem] = Field(default_factory=list)
    commercial_viability: str = ""


SignalCharacterization = Literal["quiet", "net_new", "mixed", "unknown"]


class SynthesisOutput(BaseModel):
    """Structured output for the synthesis stage (v5 — Epic 6, FR14–FR28)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 5
    run_id: str = ""
    upstream_clinical_schema_version: int | None = None
    upstream_competitor_schema_version: int | None = None
    upstream_consumer_schema_version: int | None = None
    aggregated_upstream_gaps: list[str] = Field(default_factory=list)
    ranking_criteria_version: str = "cross_domain_v1"
    ranked_opportunities: list[RankedOpportunityItem] = Field(default_factory=list)
    signal_characterization: SignalCharacterization = "unknown"
    scan_summary_lines: list[str] = Field(default_factory=list)
    note: str = "stub"


ReportFormat = Literal["markdown"]

DistributionChannel = Literal["none", "file_drop", "smtp"]
DistributionStatus = Literal["ok", "failed", "skipped"]
SlackNotifyStatus = Literal["ok", "skipped", "failed"]


class DeliveryOutput(BaseModel):
    """Structured output for the delivery stage (v3 — Epic 7 / FR18–FR19)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 3
    run_id: str = ""
    report_relative_path: str = ""
    report_format: ReportFormat = "markdown"
    report_byte_size: int = Field(default=0, ge=0)
    report_html_relative_path: str = ""
    report_html_byte_size: int = Field(default=0, ge=0)
    distribution_channel: DistributionChannel = "none"
    distribution_status: DistributionStatus = "skipped"
    distribution_detail: str = ""
    slack_notify_status: SlackNotifyStatus = "skipped"
    slack_notify_detail: str = ""
    note: str = "stub"
