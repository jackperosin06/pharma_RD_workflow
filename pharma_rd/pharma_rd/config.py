"""Central settings — use `get_settings()` everywhere; do not read os.environ ad hoc."""

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_STD_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class Settings(BaseSettings):
    """Application settings loaded from environment (PHARMA_RD_*)."""

    model_config = SettingsConfigDict(
        env_prefix="PHARMA_RD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
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

    @field_validator("competitor_regulatory_path", mode="before")
    @classmethod
    def empty_competitor_regulatory_path_is_none(cls, v: object) -> str | None:
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
            p.strip()
            for p in self.pipeline_disclosure_scopes.split(",")
            if p.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
