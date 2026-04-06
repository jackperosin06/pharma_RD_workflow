"""Central settings — use `get_settings()` everywhere; do not read os.environ ad hoc."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `.env` next to `pyproject.toml` so `PHARMA_RD_*` load correctly when the
# process cwd is the repo root (parent of this package), not only `pharma_rd/`.
_PHARMA_RD_ROOT = Path(__file__).resolve().parent.parent

_STD_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})

# FR23 / story 8.1 — comma-separated TA labels; empty string = no scope (NFR-I1).
_THERAPEUTIC_AREAS_MAX_LABELS = 32
_THERAPEUTIC_AREAS_MAX_LABEL_LEN = 128
# Unicode letters/digits/underscore, spaces, hyphen — no commas inside a label.
_THERAPEUTIC_LABEL_RE = re.compile(r"^[\w\s\-]+$", re.UNICODE)


def _normalize_and_validate_therapeutic_areas(v: str) -> str:
    """Normalize therapeutic area labels; empty string means no scope.

    Raises ValueError if any label is invalid.
    """
    s = str(v).strip()
    if not s:
        return ""
    raw_parts = s.split(",")
    labels: list[str] = []
    for i, part in enumerate(raw_parts):
        seg = part.strip()
        if not seg:
            raise ValueError(
                "PHARMA_RD_THERAPEUTIC_AREAS contains an empty label between commas "
                f"(segment index {i}); remove extra commas."
            )
        if len(seg) > _THERAPEUTIC_AREAS_MAX_LABEL_LEN:
            raise ValueError(
                "PHARMA_RD_THERAPEUTIC_AREAS label "
                f"{len(labels) + 1} exceeds max length "
                f"{_THERAPEUTIC_AREAS_MAX_LABEL_LEN} characters"
            )
        if not _THERAPEUTIC_LABEL_RE.fullmatch(seg):
            raise ValueError(
                "PHARMA_RD_THERAPEUTIC_AREAS label "
                f"{len(labels) + 1} ({seg!r}) uses disallowed characters; "
                "use letters, digits, spaces, hyphen, and underscore only "
                "(FR23 / story 8.1)."
            )
        labels.append(seg)
    if len(labels) > _THERAPEUTIC_AREAS_MAX_LABELS:
        raise ValueError(
            f"PHARMA_RD_THERAPEUTIC_AREAS has too many labels "
            f"(max {_THERAPEUTIC_AREAS_MAX_LABELS}, got {len(labels)})"
        )
    return ", ".join(labels)


# FR24 / story 8.2 — comma-separated competitor labels; empty = no watchlist (NFR-I1).
# Same label/count caps as FR23; allow & . ( ) for corporate-style identifiers.
_COMPETITOR_WATCHLIST_MAX_LABELS = 32
_COMPETITOR_WATCHLIST_MAX_LABEL_LEN = 128
_COMPETITOR_LABEL_RE = re.compile(r"^[\w\s\-&.,()]+$", re.UNICODE)


def _normalize_and_validate_competitor_watchlist(v: str) -> str:
    """Normalize competitor watchlist labels; empty string means no watchlist.

    Raises ValueError if any label is invalid.
    """
    s = str(v).strip()
    if not s:
        return ""
    raw_parts = s.split(",")
    labels: list[str] = []
    for i, part in enumerate(raw_parts):
        seg = part.strip()
        if not seg:
            raise ValueError(
                "PHARMA_RD_COMPETITOR_WATCHLIST contains an empty label between "
                f"commas (segment index {i}); remove extra commas."
            )
        if len(seg) > _COMPETITOR_WATCHLIST_MAX_LABEL_LEN:
            raise ValueError(
                "PHARMA_RD_COMPETITOR_WATCHLIST label "
                f"{len(labels) + 1} exceeds max length "
                f"{_COMPETITOR_WATCHLIST_MAX_LABEL_LEN} characters"
            )
        if not _COMPETITOR_LABEL_RE.fullmatch(seg):
            raise ValueError(
                "PHARMA_RD_COMPETITOR_WATCHLIST label "
                f"{len(labels) + 1} ({seg!r}) uses disallowed characters; "
                "use letters, digits, spaces, hyphen, underscore, "
                "ampersand, period, and parentheses only (FR24 / story 8.2)."
            )
        labels.append(seg)
    if len(labels) > _COMPETITOR_WATCHLIST_MAX_LABELS:
        raise ValueError(
            f"PHARMA_RD_COMPETITOR_WATCHLIST has too many labels "
            f"(max {_COMPETITOR_WATCHLIST_MAX_LABELS}, got {len(labels)})"
        )
    return ", ".join(labels)


def _validate_http_url(value: str, field_label: str) -> str:
    """Require http(s) URL with a host (FR25 / story 8.3)."""
    s = str(value).strip()
    p = urlparse(s)
    if p.scheme not in ("http", "https"):
        raise ValueError(
            f"{field_label} must use http or https with a host; got {value!r} "
            "(FR25 / story 8.3)."
        )
    if not p.netloc:
        raise ValueError(
            f"{field_label} must include a host; got {value!r} (FR25 / story 8.3)."
        )
    return s


class Settings(BaseSettings):
    """Application settings loaded from environment (PHARMA_RD_*)."""

    model_config = SettingsConfigDict(
        env_prefix="PHARMA_RD_",
        # Cwd `.env` first, then package-root `.env` (latter wins) so `pharma_rd/.env`
        # applies when running from the repository root without a root-level `.env`.
        env_file=(Path(".env"), _PHARMA_RD_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    deployment_profile: Literal["practice", "staging", "production"] = Field(
        default="practice",
        description=(
            "Deployment profile: practice = public/mock-capable demo build without "
            "enterprise SSO (FR26). staging/production reserve future hardening; "
            "enterprise IdP integration is FR34 roadmap, not MVP."
        ),
    )
    db_path: Path = Field(
        default=Path("data/app.db"),
        description="SQLite database file (relative to process cwd unless absolute).",
    )
    retention_days: int = Field(
        default=30,
        ge=0,
        description="Run history retention in days (NFR-R2 practice default).",
    )
    artifacts_root: Path = Field(
        default=Path("artifacts"),
        description=(
            "Root directory for per-run stage JSON artifacts (gitignored by default)."
        ),
    )
    log_level: str = Field(
        default="INFO",
        description="Root log level for pharma_rd structured JSON logs (stdout).",
    )
    schedule_cron: str = Field(
        default="0 0 * * sun",
        description=(
            "Five-field cron (minute hour day month day_of_week) for scheduled runs; "
            "default weekly Sunday 00:00 in scheduler_timezone (FR2). "
            "Use names like sun/mon for DOW — APScheduler maps 0 to Monday, not Sunday."
        ),
    )
    scheduler_timezone: str = Field(
        default="UTC",
        description=(
            "IANA timezone for interpreting schedule_cron (e.g. UTC, Europe/London)."
        ),
    )
    http_timeout_seconds: float = Field(
        default=30.0,
        ge=0.5,
        le=600.0,
        description="Total timeout (seconds) for connector HTTP reads/writes (NFR-P3).",
    )
    http_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description=(
            "Max extra attempts after the first request for transient failures."
        ),
    )
    http_retry_backoff_seconds: float = Field(
        default=0.5,
        ge=0.0,
        le=60.0,
        description="Base delay (seconds) for exponential backoff between retries.",
    )
    connector_probe_url: str | None = Field(
        default=None,
        description=(
            "When set, each pipeline stage issues a GET through the shared HTTP client "
            "before stub logic (practice/demo); leave unset to skip outbound HTTP."
        ),
    )
    therapeutic_areas: str = Field(
        default="",
        description=(
            "Comma-separated therapeutic area labels for clinical monitoring "
            "(FR23 slice). Empty means no TA scope — Clinical stage completes with "
            "explicit data_gaps (NFR-I1)."
        ),
    )
    pubmed_eutils_base: str = Field(
        default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        description="Base URL for NCBI E-utilities (override only for tests).",
    )
    pubmed_max_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Max PubMed articles to retrieve per clinical stage run (MVP cap).",
    )
    pubmed_tool_email: str | None = Field(
        default=None,
        description=(
            "Contact email for NCBI E-utilities (recommended for responsible use); "
            "passed as the email= query parameter when set."
        ),
    )
    pubmed_tool_name: str = Field(
        default="pharma_rd",
        description="tool= parameter for NCBI E-utilities requests.",
    )
    internal_research_path: str | None = Field(
        default=None,
        description=(
            "Optional JSON file or directory of *.json internal research summaries "
            "(FR7). Unset = not configured."
        ),
    )
    internal_research_max_file_bytes: int = Field(
        default=262_144,
        ge=1024,
        le=10_485_760,
        description="Max bytes per internal research JSON file (MVP guardrail).",
    )
    clinical_fixture_path: str | None = Field(
        default=None,
        description=(
            "Optional JSON file or directory of *.json with a top-level "
            '"publications" array (or a JSON array) of clinical trial publication '
            "records. When set, the clinical stage loads these rows instead of live "
            "PubMed (demo / practice)."
        ),
    )
    clinical_fixture_max_file_bytes: int = Field(
        default=262_144,
        ge=1024,
        le=10_485_760,
        description="Max bytes per clinical publication JSON fixture file.",
    )
    competitor_watchlist: str = Field(
        default="",
        description=(
            "Comma-separated competitor labels for FR8 (MVP slice of FR24). "
            "Empty means no watchlist — Competitor stage completes with explicit gaps."
        ),
    )
    competitor_observation_days: int = Field(
        default=30,
        ge=1,
        le=3650,
        description=(
            "Calendar days (UTC date arithmetic) for the observation window "
            "surfaced in integration_notes (FR8)."
        ),
    )
    competitor_regulatory_path: str | None = Field(
        default=None,
        description=(
            "Optional JSON file or directory of *.json with approvals/disclosures "
            "(practice mode). Unset = use live OpenFDA when watchlist is non-empty."
        ),
    )
    competitor_regulatory_max_file_bytes: int = Field(
        default=262_144,
        ge=1024,
        le=10_485_760,
        description="Max bytes per competitor regulatory JSON fixture file.",
    )
    openfda_drugsfda_url: str = Field(
        default="https://api.fda.gov/drug/drugsfda.json",
        description="OpenFDA drugsfda search endpoint (override for tests).",
    )
    openfda_max_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Max drugsfda records per competitor stage run (MVP cap).",
    )
    pipeline_disclosure_scopes: str = Field(
        default="",
        description=(
            "Comma-separated watch scope labels/keywords for pipeline disclosures "
            "(FR9). Empty means not configured — competitor output notes this "
            "explicitly (NFR-I1)."
        ),
    )
    consumer_feedback_path: str | None = Field(
        default=None,
        description=(
            "Optional JSON file or directory of *.json with feedback_themes "
            "(FR11 practice). Unset = use practice mock or gaps per settings."
        ),
    )
    consumer_feedback_max_file_bytes: int = Field(
        default=262_144,
        ge=1024,
        le=10_485_760,
        description="Max bytes per consumer feedback JSON fixture file.",
    )
    practice_consumer_mock: bool = Field(
        default=True,
        description=(
            "When True and consumer_feedback_path is unset, emit built-in practice "
            "themes (FR26; aligns with deployment_profile=practice). When False with "
            "no path, stage completes with data_gaps only (NFR-I1)."
        ),
    )
    pharmacy_sales_path: str | None = Field(
        default=None,
        description=(
            "Optional JSON file or directory of *.json with pharmacy_sales_trends "
            "(FR12). Unset = no pharmacy sales feed (NFR-I1 note in output)."
        ),
    )
    pharmacy_sales_max_file_bytes: int = Field(
        default=262_144,
        ge=1024,
        le=10_485_760,
        description="Max bytes per pharmacy sales JSON fixture file.",
    )
    unmet_need_demand_path: str | None = Field(
        default=None,
        description=(
            "Optional JSON file or directory of *.json with unmet_need_demand_signals "
            "(FR13). Unset = no market demand feed (NFR-I1 note in output)."
        ),
    )
    unmet_need_demand_max_file_bytes: int = Field(
        default=262_144,
        ge=1024,
        le=10_485_760,
        description="Max bytes per unmet-need / demand JSON fixture file.",
    )
    distribution_channel: Literal["none", "file_drop", "smtp"] = Field(
        default="none",
        description=(
            "FR19: none = no distribution; file_drop = copy report under "
            "distribution_drop_dir; smtp reserved (not implemented in MVP)."
        ),
    )
    distribution_drop_dir: str | None = Field(
        default=None,
        description=(
            "Directory root for file_drop copies (rd/ and marketing/ per run). "
            "Required when distribution_channel is file_drop."
        ),
    )
    rd_recipient_email: str = Field(
        default="",
        description="Optional R&D address for future SMTP (FR19).",
    )
    marketing_recipient_email: str = Field(
        default="",
        description="Optional marketing address for future SMTP (FR19).",
    )
    slack_webhook_url: str | None = Field(
        default=None,
        description=(
            "Slack incoming webhook URL for insight-run notifications (FR19). "
            "Unset = no Slack POST (NFR-S1)."
        ),
    )
    slack_webhook_timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description=(
            "Timeout for Slack webhook POST (seconds); separate from connector HTTP."
        ),
    )
    slack_bot_token: str | None = Field(
        default=None,
        description=(
            "Slack bot token (xoxb-...) for Web API file upload. Required with "
            "PHARMA_RD_SLACK_PDF_CHANNEL_ID to post report.pdf to a channel. "
            "Incoming webhooks cannot attach files (NFR-S1)."
        ),
    )
    slack_pdf_channel_id: str | None = Field(
        default=None,
        description=(
            "Slack channel ID (e.g. C0123…) for PDF upload; the bot must be a member. "
            "Unset = no PDF upload."
        ),
    )
    slack_pdf_upload_timeout_seconds: float = Field(
        default=60.0,
        ge=10.0,
        le=300.0,
        description="Timeout for Slack files.upload API (seconds).",
    )
    report_pdf_enabled: bool = Field(
        default=True,
        description=(
            "When true, render delivery/report.pdf from the HTML report (WeasyPrint). "
            "Disable in environments without PDF dependencies."
        ),
    )
    report_docx_enabled: bool = Field(
        default=True,
        description=(
            "When true, write delivery/report.docx (python-docx) for Word-friendly "
            "distribution."
        ),
    )
    openai_api_key: str | None = Field(
        default=None,
        description=(
            "OpenAI API key for GPT clinical/competitor/consumer/synthesis/report "
            "stories (NFR-S1). Unset = skip LLM steps with integration_notes. "
            "Never commit real values."
        ),
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="Chat model id for OpenAI completions (story 3.3+).",
    )
    openai_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        description="Timeout for OpenAI API calls (seconds; NFR-P3).",
    )
    openai_synthesis_timeout_seconds: float = Field(
        default=180.0,
        ge=10.0,
        le=600.0,
        description=(
            "Timeout for OpenAI synthesis stage calls (NFR-P1); may exceed "
            "openai_timeout_seconds for long cross-domain prompts."
        ),
    )
    synthesis_mode: Literal["gpt", "deterministic"] = Field(
        default="gpt",
        description=(
            "Story 6.5: gpt = OpenAI JSON synthesis when PHARMA_RD_OPENAI_API_KEY "
            "is set; if gpt and key is unset, synthesis falls back to deterministic "
            "ranking with a gap note (NFR-I1). deterministic = always use legacy "
            "ranking without LLM."
        ),
    )
    openai_report_delivery_timeout_seconds: float = Field(
        default=150.0,
        ge=10.0,
        le=600.0,
        description=(
            "Timeout for OpenAI GPT report delivery calls (story 7.6 / NFR-P1)."
        ),
    )
    report_renderer: Literal["gpt", "template"] = Field(
        default="template",
        description=(
            "Story 7.6: gpt = OpenAI narrative HTML/Markdown when API key is set; "
            "template = string-template renderer (CI default)."
        ),
    )
    report_gpt_fallback_on_error: bool = Field(
        default=True,
        description=(
            "Story 7.6: if GPT report delivery fails, fall back to template renderer "
            "and log a warning (NFR-R1)."
        ),
    )
    insight_org_display_name: str = Field(
        default="iNova",
        description=(
            "Organization name used in LLM system prompts (white-label; story 3.3)."
        ),
    )
    artifact_access_token: str | None = Field(
        default=None,
        description=(
            "Optional shared secret (FR32 / NFR-S2). When set, CLI commands that read "
            "run history or execute the pipeline require PHARMA_RD_CLI_ACCESS_TOKEN "
            "to match (constant-time compare). Unset = no guard. Never commit real "
            "values (NFR-S1)."
        ),
    )

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def empty_openai_api_key_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("openai_model", mode="before")
    @classmethod
    def openai_model_stripped(cls, v: object) -> str:
        s = str(v).strip() if v is not None else "gpt-4o"
        return s or "gpt-4o"

    @field_validator("insight_org_display_name", mode="before")
    @classmethod
    def insight_org_display_name_stripped(cls, v: object) -> str:
        if v is None:
            return "iNova"
        s = str(v).strip()
        return s if s else "iNova"

    @field_validator("artifact_access_token", mode="before")
    @classmethod
    def empty_artifact_access_token_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("artifact_access_token", mode="after")
    @classmethod
    def artifact_access_token_max_len(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) > 8192:
            raise ValueError(
                "PHARMA_RD_ARTIFACT_ACCESS_TOKEN exceeds max length 8192 "
                "(FR32 / story 8.5)."
            )
        return v

    @field_validator("connector_probe_url", mode="before")
    @classmethod
    def empty_connector_probe_url_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("internal_research_path", mode="before")
    @classmethod
    def empty_internal_research_path_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("clinical_fixture_path", mode="before")
    @classmethod
    def empty_clinical_fixture_path_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("competitor_regulatory_path", mode="before")
    @classmethod
    def empty_competitor_regulatory_path_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("consumer_feedback_path", mode="before")
    @classmethod
    def empty_consumer_feedback_path_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("pharmacy_sales_path", mode="before")
    @classmethod
    def empty_pharmacy_sales_path_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("unmet_need_demand_path", mode="before")
    @classmethod
    def empty_unmet_need_demand_path_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("distribution_drop_dir", mode="before")
    @classmethod
    def empty_distribution_drop_dir_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("slack_webhook_url", mode="before")
    @classmethod
    def empty_slack_webhook_url_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("slack_bot_token", mode="before")
    @classmethod
    def empty_slack_bot_token_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("slack_pdf_channel_id", mode="before")
    @classmethod
    def empty_slack_pdf_channel_id_is_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return None if not s else s

    @field_validator("scheduler_timezone", mode="before")
    @classmethod
    def scheduler_timezone_must_be_iana(cls, v: object) -> str:
        s = "UTC" if v is None else str(v).strip()
        if not s:
            s = "UTC"
        try:
            ZoneInfo(s)
        except Exception as e:
            raise ValueError(
                f"scheduler_timezone must be a valid IANA zone name; got {v!r}"
            ) from e
        return s

    @field_validator("deployment_profile", mode="before")
    @classmethod
    def deployment_profile_normalized(cls, v: object) -> str:
        if v is None:
            return "practice"
        s = str(v).strip().lower()
        if not s:
            return "practice"
        return s

    @field_validator("log_level", mode="before")
    @classmethod
    def log_level_must_be_std_name(cls, v: object) -> str:
        if v is None:
            return "INFO"
        s = str(v).strip().upper()
        if s not in _STD_LOG_LEVELS:
            allowed = ", ".join(sorted(_STD_LOG_LEVELS))
            raise ValueError(
                f"log_level must be one of {allowed}; got {v!r} (PHARMA_RD_LOG_LEVEL)"
            )
        return s

    @field_validator("therapeutic_areas", mode="after")
    @classmethod
    def therapeutic_areas_validated(cls, v: str) -> str:
        return _normalize_and_validate_therapeutic_areas(v)

    @field_validator("competitor_watchlist", mode="after")
    @classmethod
    def competitor_watchlist_validated(cls, v: str) -> str:
        return _normalize_and_validate_competitor_watchlist(v)

    @field_validator("pubmed_eutils_base", mode="after")
    @classmethod
    def pubmed_eutils_base_is_http_url(cls, v: str) -> str:
        return _validate_http_url(v, "PHARMA_RD_PUBMED_EUTILS_BASE")

    @field_validator("openfda_drugsfda_url", mode="after")
    @classmethod
    def openfda_drugsfda_url_is_http_url(cls, v: str) -> str:
        return _validate_http_url(v, "PHARMA_RD_OPENFDA_DRUGSFDA_URL")

    @field_validator("connector_probe_url", mode="after")
    @classmethod
    def connector_probe_url_is_http_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_http_url(v, "PHARMA_RD_CONNECTOR_PROBE_URL")

    @field_validator("slack_webhook_url", mode="after")
    @classmethod
    def slack_webhook_url_is_https(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = _validate_http_url(v, "PHARMA_RD_SLACK_WEBHOOK_URL")
        if not s.lower().startswith("https:"):
            raise ValueError(
                "PHARMA_RD_SLACK_WEBHOOK_URL must use https:// "
                "(NFR-S1 / story 8.3)."
            )
        return s

    def therapeutic_area_labels(self) -> list[str]:
        """Non-empty stripped labels from ``therapeutic_areas``."""
        if not self.therapeutic_areas.strip():
            return []
        return [p.strip() for p in self.therapeutic_areas.split(",") if p.strip()]

    def competitor_labels(self) -> list[str]:
        """Non-empty stripped labels from ``competitor_watchlist``."""
        if not self.competitor_watchlist.strip():
            return []
        return [p.strip() for p in self.competitor_watchlist.split(",") if p.strip()]

    def pipeline_disclosure_scope_labels(self) -> list[str]:
        """Non-empty stripped labels from ``pipeline_disclosure_scopes`` (FR9)."""
        if not self.pipeline_disclosure_scopes.strip():
            return []
        return [
            p.strip() for p in self.pipeline_disclosure_scopes.split(",") if p.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
