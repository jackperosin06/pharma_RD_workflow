"""Shared OpenAI SDK wiring for GPT enrichment steps (stories 3.3, 4.4+)."""

from __future__ import annotations

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from pharma_rd.config import Settings


def create_openai_client(settings: Settings) -> OpenAI:
    """Instantiate OpenAI client with API key and timeout from settings."""
    key = settings.openai_api_key
    if not key:
        raise ValueError("openai_api_key is required to create OpenAI client")
    return OpenAI(api_key=key, timeout=settings.openai_timeout_seconds)


def create_openai_client_for_synthesis(settings: Settings) -> OpenAI:
    """OpenAI client using synthesis-specific timeout (story 6.5 / NFR-P1)."""
    key = settings.openai_api_key
    if not key:
        raise ValueError("openai_api_key is required to create OpenAI client")
    return OpenAI(
        api_key=key,
        timeout=settings.openai_synthesis_timeout_seconds,
    )


def create_openai_client_for_report_delivery(settings: Settings) -> OpenAI:
    """OpenAI client for GPT report delivery (story 7.6 / NFR-P1)."""
    key = settings.openai_api_key
    if not key:
        raise ValueError("openai_api_key is required to create OpenAI client")
    return OpenAI(
        api_key=key,
        timeout=settings.openai_report_delivery_timeout_seconds,
    )


def run_chat_json_completion(
    client: OpenAI,
    *,
    model: str,
    system: str,
    user_content: str,
) -> tuple[str | None, str | None]:
    """Call chat.completions with JSON object format; return (content, err)."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
    except (APIConnectionError, APITimeoutError, RateLimitError, APIStatusError) as e:
        return None, f"{type(e).__name__}: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

    if not resp.choices:
        return None, "no_completion_choices"

    msg = resp.choices[0].message
    if msg is None:
        return None, "no_message"
    choice = msg.content
    if choice is None or not str(choice).strip():
        return None, "empty_model_response"
    return str(choice), None
