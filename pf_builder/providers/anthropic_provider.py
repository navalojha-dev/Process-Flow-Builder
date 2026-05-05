"""Anthropic Claude provider."""
from __future__ import annotations

import os

import anthropic

from .base import Provider, StageResult, extract_json


class AnthropicProvider(Provider):
    name = "anthropic"
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("PF_ANTHROPIC_MODEL", self.DEFAULT_MODEL)
        self._client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from env

    def ask(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> StageResult:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text
            for block in resp.content
            if getattr(block, "type", None) == "text"
        )
        data = extract_json(text)
        return StageResult(
            data=data,
            raw_text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=self.model,
            provider=self.name,
        )
