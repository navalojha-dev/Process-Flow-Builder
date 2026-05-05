"""Google AI Studio (Gemini) provider — raw REST.

We deliberately do NOT use `google-genai` SDK here. Two reasons:
1. Bundle size — the SDK pulls in ~20MB of grpc/proto deps that bust
   Vercel's 50MB function-package limit.
2. We only need one endpoint (`generateContent`) and we already use
   httpx everywhere. One HTTP call beats a heavy SDK.

Auth: a single GEMINI_API_KEY env var (https://aistudio.google.com/apikey).
"""
from __future__ import annotations

import os

import httpx

from .base import Provider, StageResult, extract_json

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(Provider):
    name = "gemini"
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, model: str | None = None) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get one at "
                "https://aistudio.google.com/apikey and `export GEMINI_API_KEY=...`."
            )
        self.api_key = api_key
        self.model = model or os.environ.get("PF_GEMINI_MODEL", self.DEFAULT_MODEL)
        self._client = httpx.Client(timeout=60.0)

    def ask(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> StageResult:
        # Build generationConfig. Two reliability levers we set unconditionally
        # for structured-JSON tasks:
        #   1. responseMimeType="application/json" — forces the model to emit
        #      valid JSON. Without this, Flash sometimes early-terminates mid
        #      output and reports finish_reason=STOP (we hit this on Stage 2).
        #   2. thinkingConfig.thinkingBudget=0 on Flash — so the budget goes
        #      to visible JSON output rather than silent chain-of-thought
        #      tokens that count against the same cap.
        gen_cfg: dict = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        }
        if "flash" in self.model.lower():
            gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}

        url = f"{API_BASE}/models/{self.model}:generateContent"
        try:
            resp = self._client.post(
                url,
                params={"key": self.api_key},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": gen_cfg,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Gemini API error {e.response.status_code}: "
                f"{e.response.text[:400]}"
            ) from e

        body = resp.json()

        # Extract text from candidates
        candidates = body.get("candidates", [])
        if not candidates:
            raise RuntimeError(
                f"Gemini returned no candidates. Response: {str(body)[:400]}"
            )
        cand = candidates[0]
        finish = cand.get("finishReason")
        parts = cand.get("content", {}).get("parts", []) or []
        text = "".join(p.get("text", "") for p in parts)

        usage = body.get("usageMetadata", {})
        in_tokens = usage.get("promptTokenCount", 0)
        out_tokens = usage.get("candidatesTokenCount", 0)
        thinking_tokens = usage.get("thoughtsTokenCount", 0)

        # Detect truncation — visible JSON unfinished.
        looks_truncated = "```json" in text and (
            text.count("```") < 2  # opening fence with no closing fence
        )
        if finish == "MAX_TOKENS" or looks_truncated:
            raise RuntimeError(
                f"Gemini truncated the response (finish_reason={finish}). "
                f"Budget: max_output_tokens={max_tokens}. Used: "
                f"prompt={in_tokens}, output={out_tokens}, "
                f"thinking={thinking_tokens}. "
                f"Bump max_tokens for this stage or shorten the prompt. "
                f"First 200 chars:\n{text[:200]}"
            )

        data = extract_json(text)
        return StageResult(
            data=data,
            raw_text=text,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            model=self.model,
            provider=self.name,
        )
