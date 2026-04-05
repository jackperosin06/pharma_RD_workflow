"""Coarse CLI access control (FR32 / NFR-S2, story 8.5)."""

from __future__ import annotations

import hmac
import os
import sys

from pharma_rd.config import get_settings


def cli_access_exit_code() -> int | None:
    """If FR32 guard is enabled, require matching ``PHARMA_RD_CLI_ACCESS_TOKEN``.

    Returns an exit code (1) when access is denied, or ``None`` when allowed.
    Does not log secrets (NFR-S1).
    """
    settings = get_settings()
    expected = settings.artifact_access_token
    if not expected:
        return None
    provided = os.environ.get("PHARMA_RD_CLI_ACCESS_TOKEN")
    if not provided or not str(provided).strip():
        print(
            "pharma_rd: access denied — set PHARMA_RD_CLI_ACCESS_TOKEN to match "
            "PHARMA_RD_ARTIFACT_ACCESS_TOKEN (FR32).",
            file=sys.stderr,
        )
        return 1
    prov = str(provided).strip()
    try:
        exp_bytes = expected.encode("utf-8")
        prov_bytes = prov.encode("utf-8")
    except UnicodeEncodeError:
        print("pharma_rd: access denied (invalid token)", file=sys.stderr)
        return 1
    if len(exp_bytes) != len(prov_bytes):
        print("pharma_rd: access denied (invalid token)", file=sys.stderr)
        return 1
    if not hmac.compare_digest(exp_bytes, prov_bytes):
        print("pharma_rd: access denied (invalid token)", file=sys.stderr)
        return 1
    return None
