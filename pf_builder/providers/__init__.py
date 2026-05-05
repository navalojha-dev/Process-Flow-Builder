"""LLM provider implementations.

Each provider exposes the same `Provider.ask(...)` interface. Stages
talk to providers only via `pf_builder.llm.ask_for_json(...)`, so the
choice of provider is invisible to stage code.

Selection precedence (highest first):
  1. `provider=` kwarg passed to `ask_for_json`
  2. `PF_PROVIDER` env var
  3. Default: "anthropic"
"""
from __future__ import annotations

from .base import Provider, StageResult


def get_provider(name: str) -> Provider:
    """Factory. Imports the chosen provider lazily so missing SDKs only
    blow up when actually requested."""
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider()
    raise ValueError(
        f"Unknown provider: {name!r}. Supported: anthropic, gemini."
    )


__all__ = ["Provider", "StageResult", "get_provider"]
