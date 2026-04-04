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

    @field_validator("connector_probe_url", mode="before")
    @classmethod
    def empty_connector_probe_url_is_none(cls, v: object) -> str | None:
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
