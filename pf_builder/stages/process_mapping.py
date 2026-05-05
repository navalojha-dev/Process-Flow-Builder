"""Stage 3 — Process Mapping (As-Is / To-Be / Impact matrix).

Reads the profile + the just-designed flow + transcript, and writes
the slide-2 matrix: 4-7 business processes, each with 2-5 as-is /
to-be / impact bullets. To-be bullets cite Shipsy capabilities by id.
"""
from __future__ import annotations

import json

from ..kb.catalog import capabilities_for_prompt, vertical_for_prompt
from ..llm import StageResult, ask_for_json

SYSTEM = """You write the As-Is / To-Be / Impact matrix for slide 2 of a Shipsy client deck.

Output ONLY a JSON array inside a fenced ```json block. After the block you may write 1-5 lines of "notes:" — one per line — flagging anything you assumed or where the transcript was thin.

EACH MATRIX ROW corresponds to ONE business process this client cares about. The matrix is the place to make the SE's case to a buyer: pain → solution → outcome. Be concrete and grounded in the transcript.

RULES:
- 4-7 rows total.
- Per row: 2-5 bullets in each of as_is, to_be, impact.
- Bullets are short — one sentence, ideally < 100 chars.
- as_is = pain in their CURRENT stack. Use signals from the transcript (tools they use, manual workarounds, missing visibility).
- to_be = how Shipsy solves it. Cite capability ids in [brackets] where relevant — e.g. "[routing-engine] handles 200+ constraints natively".
- impact = business outcome. Numbers if the transcript has them; qualitative otherwise.
- Order rows by buyer relevance — biggest pain first.

OUTPUT JSON SHAPE:
[
  {
    "process": "<name of the business process>",
    "as_is":   ["<bullet>", "<bullet>", ...],
    "to_be":   ["<bullet>", "<bullet>", ...],
    "impact":  ["<bullet>", "<bullet>", ...]
  }
]

CAPABILITIES_PLACEHOLDER

VERTICAL_PLAYBOOK_PLACEHOLDER
"""

USER_TEMPLATE = """CLIENT PROFILE:
{profile_json}

PROCESS FLOW (slide 1 — already designed):
{flow_json}

TRANSCRIPT:
<<<
{transcript}
>>>

Write the As-Is / To-Be / Impact matrix. 4-7 rows."""


def run(
    *,
    profile: dict,
    process_flow: dict,
    transcript: str,
) -> StageResult:
    system = (
        SYSTEM
        .replace("CAPABILITIES_PLACEHOLDER", capabilities_for_prompt())
        .replace(
            "VERTICAL_PLAYBOOK_PLACEHOLDER",
            vertical_for_prompt(profile.get("vertical", "other")),
        )
    )
    user = USER_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2),
        flow_json=json.dumps(process_flow, indent=2),
        transcript=transcript.strip(),
    )
    return ask_for_json(system=system, user=user, max_tokens=7000)
