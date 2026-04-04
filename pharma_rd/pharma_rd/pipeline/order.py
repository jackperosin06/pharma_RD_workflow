"""Pipeline stage order and edges — lightweight; safe for operator CLI imports."""

from __future__ import annotations

# Fixed execution order (PRD / architecture).
PIPELINE_ORDER: tuple[str, ...] = (
    "clinical",
    "competitor",
    "consumer",
    "synthesis",
    "delivery",
)

# Previous stage key for each non-root stage (explicit wiring for operators / retries).
PIPELINE_EDGES: dict[str, str | None] = {
    "clinical": None,
    "competitor": "clinical",
    "consumer": "competitor",
    "synthesis": "consumer",
    "delivery": "synthesis",
}
