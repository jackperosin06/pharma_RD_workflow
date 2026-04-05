"""Coarse CLI access guard (story 8.5)."""

from __future__ import annotations

import pytest


def test_cli_access_exit_code_denied_when_token_not_utf8_encodable(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pharma_rd import access_control as ac

    class _Tok:
        artifact_access_token = "\ud800"

    monkeypatch.setattr(ac, "get_settings", lambda: _Tok())
    monkeypatch.setenv("PHARMA_RD_CLI_ACCESS_TOKEN", "x")

    assert ac.cli_access_exit_code() == 1
    assert "access denied" in capsys.readouterr().err.lower()
