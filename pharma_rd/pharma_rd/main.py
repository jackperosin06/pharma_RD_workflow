"""CLI entrypoint for local development and future pipeline triggers."""

from pharma_rd.config import get_settings


def main() -> None:
    """Print a minimal status line using configured environment (story 1.1 scaffold)."""
    settings = get_settings()
    print(f"pharma_rd ready (env={settings.env})")
