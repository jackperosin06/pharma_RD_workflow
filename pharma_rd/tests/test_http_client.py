"""Tests for shared httpx connector (timeouts, bounded retries, backoff)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from pharma_rd.http_client import (
    ConnectorFailure,
    IntegrationErrorClass,
    request_with_retries,
)


def test_request_succeeds_first_try(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_HTTP_MAX_RETRIES", "2")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)
    try:
        r = request_with_retries(
            "GET",
            "http://example.test/",
            client=client,
        )
        assert r.status_code == 200
    finally:
        client.close()


def test_retries_transient_http_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_HTTP_MAX_RETRIES", "3")
    monkeypatch.setenv("PHARMA_RD_HTTP_RETRY_BACKOFF_SECONDS", "0")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    n = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        n["i"] += 1
        if n["i"] < 3:
            return httpx.Response(503)
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)
    try:
        r = request_with_retries("GET", "http://example.test/r", client=client)
        assert r.status_code == 200
        assert n["i"] == 3
    finally:
        client.close()


def test_transient_exhausted_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_HTTP_MAX_RETRIES", "1")
    monkeypatch.setenv("PHARMA_RD_HTTP_RETRY_BACKOFF_SECONDS", "0")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)
    try:
        with pytest.raises(ConnectorFailure) as ei:
            request_with_retries("GET", "http://example.test/fail", client=client)
        assert ei.value.error_class is IntegrationErrorClass.TRANSIENT_EXHAUSTED
    finally:
        client.close()


def test_non_retryable_4xx_raises_http_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHARMA_RD_HTTP_MAX_RETRIES", "3")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, follow_redirects=True)
    try:
        with pytest.raises(ConnectorFailure) as ei:
            request_with_retries("GET", "http://example.test/missing", client=client)
        assert ei.value.error_class is IntegrationErrorClass.HTTP_CLIENT_ERROR
    finally:
        client.close()


def test_timeout_retries_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_HTTP_MAX_RETRIES", "2")
    monkeypatch.setenv("PHARMA_RD_HTTP_RETRY_BACKOFF_SECONDS", "0")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    mock_client = MagicMock()
    mock_client.request.side_effect = [
        httpx.TimeoutException("read timeout"),
        httpx.Response(200),
    ]

    try:
        r = request_with_retries(
            "GET",
            "http://example.test/t",
            client=mock_client,
        )
        assert r.status_code == 200
        assert mock_client.request.call_count == 2
    finally:
        pass


def test_timeout_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_HTTP_MAX_RETRIES", "0")
    monkeypatch.setenv("PHARMA_RD_HTTP_RETRY_BACKOFF_SECONDS", "0")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    mock_client = MagicMock()
    mock_client.request.side_effect = httpx.TimeoutException("timeout")

    with pytest.raises(ConnectorFailure) as ei:
        request_with_retries("GET", "http://example.test/x", client=mock_client)
    assert ei.value.error_class is IntegrationErrorClass.TIMEOUT


def test_connection_retries_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHARMA_RD_HTTP_MAX_RETRIES", "0")
    monkeypatch.setenv("PHARMA_RD_HTTP_RETRY_BACKOFF_SECONDS", "0")
    from pharma_rd.config import get_settings

    get_settings.cache_clear()

    mock_client = MagicMock()
    mock_client.request.side_effect = httpx.ConnectError("refused")

    with pytest.raises(ConnectorFailure) as ei:
        request_with_retries("GET", "http://example.test/nope", client=mock_client)
    assert ei.value.error_class is IntegrationErrorClass.CONNECTION
