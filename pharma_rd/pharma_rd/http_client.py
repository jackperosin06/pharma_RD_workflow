"""Shared httpx connector: timeouts, retries, exponential backoff (story 2.2)."""

from __future__ import annotations

import time
from enum import StrEnum

import httpx

from pharma_rd.config import get_settings
from pharma_rd.logging_setup import get_pipeline_logger

_log = get_pipeline_logger("pharma_rd.http_client")

# Retry only likely-transient HTTP statuses (do not retry arbitrary 4xx).
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class IntegrationErrorClass(StrEnum):
    """NFR-I2-style classification for connector failures."""

    TIMEOUT = "timeout"
    TRANSIENT_EXHAUSTED = "transient_exhausted"
    CONNECTION = "connection"
    HTTP_CLIENT_ERROR = "http_client_error"


class ConnectorFailure(RuntimeError):
    """Raised when outbound HTTP fails after retries or on non-retryable errors."""

    def __init__(
        self,
        message: str,
        *,
        error_class: IntegrationErrorClass,
    ) -> None:
        super().__init__(message)
        self.error_class = error_class


def _backoff_seconds(base: float, attempt_index: int) -> float:
    """Exponential backoff: base * 2**attempt_index."""
    return base * (2**attempt_index)


def request_with_retries(
    method: str,
    url: str,
    *,
    stage_key: str | None = None,
    client: httpx.Client | None = None,
    allow_statuses: frozenset[int] | None = None,
) -> httpx.Response:
    """Perform an HTTP request using shared timeout and retry policy from settings.

    Retries transient failures: timeouts, connection errors, and HTTP
    429 / 500 / 502 / 503 / 504 up to ``http_max_retries`` with exponential backoff.
    Does not log request bodies or secrets.

    ``allow_statuses``: HTTP status codes to return as-is instead of raising
    (e.g. OpenFDA uses 404 + JSON ``NOT_FOUND`` for zero search hits).
    """
    settings = get_settings()
    timeout = httpx.Timeout(
        connect=min(10.0, settings.http_timeout_seconds),
        read=settings.http_timeout_seconds,
        write=settings.http_timeout_seconds,
        pool=settings.http_timeout_seconds,
    )
    max_extra = settings.http_max_retries
    base_backoff = settings.http_retry_backoff_seconds
    own_client = client is None
    if client is None:
        client = httpx.Client(timeout=timeout, follow_redirects=True)

    extra_log: dict[str, object] = {}
    if stage_key is not None:
        extra_log["stage"] = stage_key

    try:
        attempt = 0
        while True:
            try:
                response = client.request(method.upper(), url)
            except httpx.TimeoutException as e:
                if attempt >= max_extra:
                    raise ConnectorFailure(
                        f"HTTP timeout after {max_extra + 1} attempt(s) "
                        f"calling {url!r}: {e}",
                        error_class=IntegrationErrorClass.TIMEOUT,
                    ) from e
                sleep_s = _backoff_seconds(base_backoff, attempt)
                _log.info(
                    "connector retry after timeout",
                    extra={
                        "event": "connector_retry",
                        "outcome": None,
                        "attempt": attempt + 1,
                        "max_attempts": max_extra + 1,
                        "next_backoff_s": sleep_s,
                        **extra_log,
                    },
                )
                time.sleep(sleep_s)
                attempt += 1
                continue
            except httpx.RequestError as e:
                if attempt >= max_extra:
                    raise ConnectorFailure(
                        f"HTTP connection failed after {max_extra + 1} attempt(s) "
                        f"calling {url!r}: {e}",
                        error_class=IntegrationErrorClass.CONNECTION,
                    ) from e
                sleep_s = _backoff_seconds(base_backoff, attempt)
                _log.info(
                    "connector retry after connection error",
                    extra={
                        "event": "connector_retry",
                        "outcome": None,
                        "attempt": attempt + 1,
                        "max_attempts": max_extra + 1,
                        "next_backoff_s": sleep_s,
                        **extra_log,
                    },
                )
                time.sleep(sleep_s)
                attempt += 1
                continue

            code = response.status_code
            if code in _RETRYABLE_STATUS:
                if attempt >= max_extra:
                    raise ConnectorFailure(
                        f"HTTP {code} from {url!r} persisted after "
                        f"{max_extra + 1} attempt(s); "
                        f"giving up (transient errors exhausted).",
                        error_class=IntegrationErrorClass.TRANSIENT_EXHAUSTED,
                    )
                sleep_s = _backoff_seconds(base_backoff, attempt)
                _log.info(
                    "connector retry after HTTP error status",
                    extra={
                        "event": "connector_retry",
                        "outcome": None,
                        "attempt": attempt + 1,
                        "max_attempts": max_extra + 1,
                        "http_status": code,
                        "next_backoff_s": sleep_s,
                        **extra_log,
                    },
                )
                time.sleep(sleep_s)
                attempt += 1
                continue

            if code >= 400:
                if allow_statuses is not None and code in allow_statuses:
                    return response
                raise ConnectorFailure(
                    f"HTTP {code} from {url!r} is not retryable; "
                    f"fix URL, auth, or payload.",
                    error_class=IntegrationErrorClass.HTTP_CLIENT_ERROR,
                )

            return response
    finally:
        if own_client:
            client.close()
