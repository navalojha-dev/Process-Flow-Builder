"""Stages talk to the LLM only via this module — never directly to a
provider SDK. That's the seam that lets us swap Anthropic ↔ Gemini in
one line.

Selection precedence:
  1. `provider=` kwarg on `ask_for_json`
  2. `PF_PROVIDER` env var (set by `pf build --provider …`)
  3. Default: "anthropic"
"""
from __future__ import annotations

import os

from .providers import StageResult, get_provider

DEFAULT_MAX_TOKENS = 4096


def _selected_provider_name(explicit: str | None) -> str:
    return explicit or os.environ.get("PF_PROVIDER", "anthropic")


def ask_for_json(
    *,
    system: str,
    user: str,
    provider: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 0.2,
) -> StageResult:
    """Send `system` + `user` to the chosen LLM, return parsed JSON + usage.

    Both providers share the same prompt contract: the model emits a
    fenced ```json block, optionally followed by trailing "assumptions:"
    or "notes:" prose. The extractor handles both fenced and bare JSON.
    """
    name = _selected_provider_name(provider)
    p = get_provider(name)
    return p.ask(
        system=system,
        user=user,
        max_tokens=max_tokens,
        temperature=temperature,
    )


# Re-export for convenient `from pf_builder.llm import StageResult`
__all__ = ["StageResult", "ask_for_json"]
