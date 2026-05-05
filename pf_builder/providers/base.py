"""Provider interface — every LLM backend implements this contract."""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass
class StageResult:
    data: Any
    raw_text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str


def extract_json(text: str) -> Any:
    """Pull a JSON object/array out of a model response.

    Handles three cases:
      1. A fenced ```json ... ``` block — preferred. Both providers are
         instructed to emit this so they can also include trailing
         "assumptions:" prose without breaking the parser.
      2. A bare top-level { ... } or [ ... ] (Gemini in JSON mode).
      3. Failure — caller may retry with a stricter prompt.
    """
    m = _FENCE_RE.search(text)
    if m:
        return json.loads(m.group(1).strip())

    # If we see an opening ```json with no closing fence, the response was
    # almost certainly truncated mid-output. Give a useful error.
    if "```json" in text or text.lstrip().startswith("```"):
        raise ValueError(
            "Model response opened a ```json fence but never closed it — "
            "the output was truncated mid-JSON (likely hit max_tokens). "
            "Bump max_tokens for this stage. First 400 chars:\n"
            + text[:400]
        )

    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ValueError(
        f"Could not extract JSON from model response. First 400 chars:\n{text[:400]}"
    )


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    def ask(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> StageResult: ...
