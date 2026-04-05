"""OpenAI GPT cross-domain synthesis (story 6.5 / FR14–FR17, FR27–FR28)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import ValidationError

from pharma_rd.config import Settings
from pharma_rd.integrations.openai_client import (
    create_openai_client_for_synthesis,
    run_chat_json_completion,
)
from pharma_rd.pipeline.contracts import (
    ClinicalOutput,
    CompetitorOutput,
    ConsumerOutput,
    RankedOpportunityItem,
    SignalCharacterization,
)

_SYSTEM_PROMPT = (
    "You are a senior pharmaceutical strategy advisor for {org}. "
    "Synthesize cross-domain monitoring signals (clinical, competitor/regulatory, "
    "consumer/market) into ranked line-extension opportunities. "
    "The user message is JSON with keys clinical, competitor, consumer — each is "
    "the full structured stage output, including optional GPT enrichment objects "
    "clinical_gpt_analysis, competitor_gpt_analysis, consumer_gpt_analysis "
    "when present. "
    "Respond with a single JSON object only, using exactly these keys: "
    '"ranked_opportunities" (array), "signal_characterization" (string). '
    "Each ranked_opportunities element MUST have: "
    '"rank" (integer >= 1), "title", "rationale_short", '
    '"domain_coverage" (object with boolean keys clinical, competitor, consumer), '
    '"evidence_references" (array of {{domain, label, reference}} with domain one of '
    '"clinical"|"competitor"|"consumer"), '
    '"commercial_viability". '
    'signal_characterization MUST be one of: "quiet", "net_new", "mixed", "unknown". '
    "Cite evidence using reference strings that appear in the user JSON only; "
    "do not invent PMIDs, URLs, or identifiers not present in the input. "
    "At most 10 ranked rows."
)

_MAX_RANKED_GPT = 10


@dataclass(frozen=True)
class GptSynthesisPartial:
    ranked_opportunities: list[RankedOpportunityItem]
    signal_characterization: SignalCharacterization
    operator_notes: tuple[str, ...] = ()


def _build_user_payload(
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> str:
    """Serialize upstream outputs; per-list caps limit prompt size (see README)."""
    max_items = 40

    def cap_clinical(c: ClinicalOutput) -> dict[str, object]:
        d = c.model_dump(mode="json")
        notes: list[str] = []
        for key in ("publication_items", "internal_research_items"):
            arr = d.get(key)
            if isinstance(arr, list) and len(arr) > max_items:
                d[key] = arr[:max_items]
                notes.append(f"{key} truncated to {max_items} items for prompt size.")
        if notes:
            d["_synthesis_prompt_notes"] = notes
        return d

    def cap_competitor(p: CompetitorOutput) -> dict[str, object]:
        d = p.model_dump(mode="json")
        notes: list[str] = []
        for key in (
            "approval_items",
            "disclosure_items",
            "pipeline_disclosure_items",
            "patent_filing_flags",
        ):
            arr = d.get(key)
            if isinstance(arr, list) and len(arr) > max_items:
                d[key] = arr[:max_items]
                notes.append(f"{key} truncated to {max_items} items for prompt size.")
        if notes:
            d["_synthesis_prompt_notes"] = notes
        return d

    def cap_consumer(u: ConsumerOutput) -> dict[str, object]:
        d = u.model_dump(mode="json")
        notes: list[str] = []
        for key in (
            "feedback_themes",
            "pharmacy_sales_trends",
            "unmet_need_demand_signals",
        ):
            arr = d.get(key)
            if isinstance(arr, list) and len(arr) > max_items:
                d[key] = arr[:max_items]
                notes.append(f"{key} truncated to {max_items} items for prompt size.")
        if notes:
            d["_synthesis_prompt_notes"] = notes
        return d

    payload = {
        "clinical": cap_clinical(clinical),
        "competitor": cap_competitor(competitor),
        "consumer": cap_consumer(consumer),
    }
    return json.dumps(payload, ensure_ascii=False)


def _parse_partial(data: object) -> GptSynthesisPartial:
    if not isinstance(data, dict):
        raise ValueError("model response must be a JSON object")
    raw_ranked = data.get("ranked_opportunities")
    if not isinstance(raw_ranked, list):
        raise ValueError("ranked_opportunities must be an array")
    ranked: list[RankedOpportunityItem] = []
    for i, row in enumerate(raw_ranked):
        if not isinstance(row, dict):
            raise ValueError(f"ranked_opportunities[{i}] must be an object")
        ranked.append(RankedOpportunityItem.model_validate(row))
    notes: list[str] = []
    n_ranked = len(ranked)
    if n_ranked > _MAX_RANKED_GPT:
        ranked = ranked[:_MAX_RANKED_GPT]
        notes.append(
            f"[synthesis] GPT returned {n_ranked} ranked rows; "
            f"truncated to {_MAX_RANKED_GPT}."
        )
    sig = data.get("signal_characterization", "unknown")
    if sig not in ("quiet", "net_new", "mixed", "unknown"):
        raise ValueError("signal_characterization must be quiet|net_new|mixed|unknown")
    return GptSynthesisPartial(
        ranked_opportunities=ranked,
        signal_characterization=sig,  # type: ignore[arg-type]
        operator_notes=tuple(notes),
    )


def _format_validation_errors(exc: ValidationError | ValueError) -> str:
    if isinstance(exc, ValidationError):
        return exc.json(indent=None)[:4000]
    return str(exc)[:4000]


def call_synthesis_gpt(
    settings: Settings,
    clinical: ClinicalOutput,
    competitor: CompetitorOutput,
    consumer: ConsumerOutput,
) -> tuple[GptSynthesisPartial | None, str | None]:
    """Call OpenAI; return (partial, None) or (None, operator_error_message).

    Policy (story 6.5): one bounded retry with a repair prompt if JSON parse or
    Pydantic validation fails; no silent fallback to deterministic synthesis.
    """
    if not settings.openai_api_key:
        return None, "missing_api_key"

    client = create_openai_client_for_synthesis(settings)
    system = _SYSTEM_PROMPT.format(org=settings.insight_org_display_name)
    user_content = _build_user_payload(clinical, competitor, consumer)

    def _complete(user: str) -> tuple[str | None, str | None]:
        return run_chat_json_completion(
            client,
            model=settings.openai_model,
            system=system,
            user_content=user,
        )

    choice, err = _complete(user_content)
    if err:
        return None, err
    if not choice or not choice.strip():
        return None, "empty_model_response"

    def _parse_choice(text: str) -> GptSynthesisPartial:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON: {e}") from e
        return _parse_partial(data)

    try:
        return _parse_choice(choice), None
    except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as e:
        last_err = (
            _format_validation_errors(e)
            if isinstance(e, ValidationError)
            else str(e)
        )
        repair = (
            user_content
            + "\n\n---\nThe previous model output failed validation. "
            "Respond again with a single JSON object only.\n"
            f"Error detail:\n{last_err}\n"
        )
        choice2, err2 = _complete(repair)
        if err2:
            return None, f"synthesis_gpt_retry_failed: {err2}"
        if not choice2 or not choice2.strip():
            return None, "empty_model_response_on_retry"
        try:
            return _parse_choice(choice2), None
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as e2:
            det = (
                _format_validation_errors(e2)
                if isinstance(e2, ValidationError)
                else str(e2)
            )
            return None, f"synthesis_gpt_validation_failed: {det}"
