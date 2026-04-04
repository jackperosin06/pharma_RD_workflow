"""Optional per-stage HTTP probe via shared connector settings (story 2.2)."""

from __future__ import annotations

from pharma_rd.config import get_settings
from pharma_rd.http_client import request_with_retries


def ensure_connector_probe(stage_key: str) -> None:
    """GET ``connector_probe_url`` when set, using shared timeout/retry policy."""
    url = get_settings().connector_probe_url
    if not url:
        return
    request_with_retries("GET", url, stage_key=stage_key)
