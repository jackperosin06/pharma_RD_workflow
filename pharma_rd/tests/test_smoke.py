"""Smoke tests for package import and settings."""

import subprocess
import sys
from pathlib import Path

from pharma_rd import __version__
from pharma_rd.config import Settings, get_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_default() -> None:
    get_settings.cache_clear()
    s = get_settings()
    assert isinstance(s, Settings)
    assert s.env == "development"
    assert s.deployment_profile == "practice"


def test_python_module_entrypoint_exits_zero() -> None:
    """Subprocess `python -m pharma_rd` (matches AC2 / `uv run python -m pharma_rd`)."""
    result = subprocess.run(
        [sys.executable, "-m", "pharma_rd"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "run" in result.stdout
    assert "scheduler" in result.stdout
    assert "retry-stage" in result.stdout
