"""Central settings — use `get_settings()` everywhere; do not read os.environ ad hoc."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
