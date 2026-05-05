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

OUTPUT FORMAT (strict — no exceptions):
- Output a single JSON array. The array contains 4 to 7 elements.
- Each element MUST be a JSON OBJECT with exactly these four fields:
    "process" (string),
    "as_is"  (array of 2-5 short bullet strings),
    "to_be"  (array of 2-5 short bullet strings),
    "impact" (array of 2-5 short bullet strings)
- DO NOT wrap in an outer object. DO NOT output a list of strings. DO NOT include any other text.

CONCRETE EXAMPLE of valid output (this exact shape, with your own values):
[
  {
    "process": "Delivery Plan Optimization",
    "as_is": ["12 planners spend 3-4 hrs/day in Roadnet per DC", "Excel macro for holds/returns then re-imported"],
    "to_be": ["[routing-engine] handles 200+ constraints natively (Ramadan, school, cameras)", "Native order selection / holds / returns — no Excel"],
    "impact": ["Planner effort drops sharply (3-4 hrs → ~1 hr per DC)", "Trucks/day reduce 200 → 180-190 at same SLA window"]
  }
]

CONTENT RULES:
- Each row corresponds to ONE business process this client cares about. Order rows by buyer relevance — biggest pain first.
- Bullets are short — one sentence, ideally < 100 chars.
- as_is = pain in CURRENT stack. Use transcript signals (tools they use, manual workarounds, missing visibility).
- to_be = how Shipsy solves it. Cite capability ids in [brackets] where relevant.
- impact = business outcome. Numbers if the transcript has them; qualitative otherwise.

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
