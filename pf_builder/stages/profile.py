"""Stage 1 — Client profile extraction.

Reads the raw transcript + the user-provided client_name (and optional
vertical_hint) and returns the `client` block of the flow JSON, plus a
list of assumptions the model had to make.
"""
from __future__ import annotations

from ..kb.catalog import VERTICAL_NAMES
from ..llm import StageResult, ask_for_json

SYSTEM = """You extract a structured client profile from a raw sales-meeting transcript for a Shipsy logistics-tech process-flow deck.

You output ONLY a JSON object inside a fenced ```json block. After the block you may write 1-5 lines of "assumptions:" — one per line — listing fields you had to infer because the transcript was silent on them.

Schema you must match exactly:
{
  "name":              "<full client name — use the user-provided value verbatim>",
  "short":             "<short label for inline use, ≤ 12 chars>",
  "industry_vertical": "<one short line, e.g. 'Container Drayage · Port + Cross-border Trucking'>",
  "geography":         "<countries / regions of operation>",
  "load_type":         "<what they ship: containers, cases, pallets, parcels, etc.>",
  "business_model":    "<B2B / B2C, in-house vs subcontracted, asset model>",
  "mile_stages":       ["first_mile" | "middle_mile" | "last_mile" | "reverse"],
  "vertical":          "<one of: VERTICAL_LIST — pick the closest>"
}

Rules:
- Take `name` verbatim from what the user supplied. Don't reword it.
- `short` should be at most 12 chars (e.g. 'DP World', 'Aljomaih', 'TPN').
- `vertical` MUST be one of the allowed values. If unsure, pick "other".
- `mile_stages` should reflect what this client actually operates — only include stages mentioned in the transcript.
"""

USER_TEMPLATE = """CLIENT NAME (authoritative, use verbatim): {client_name}
VERTICAL HINT (may be empty — use only if transcript is silent): {vertical_hint}

TRANSCRIPT:
<<<
{transcript}
>>>

Produce the JSON profile."""


def run(
    *,
    transcript: str,
    client_name: str,
    vertical_hint: str | None = None,
) -> StageResult:
    system = SYSTEM.replace("VERTICAL_LIST", ", ".join(VERTICAL_NAMES))
    user = USER_TEMPLATE.format(
        client_name=client_name,
        vertical_hint=vertical_hint or "(none)",
        transcript=transcript.strip(),
    )
    return ask_for_json(system=system, user=user, max_tokens=1024)
