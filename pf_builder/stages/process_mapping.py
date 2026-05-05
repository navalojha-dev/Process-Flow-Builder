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

OUTPUT FORMAT (strict):
- Output a single JSON array of 4 to 7 row objects.
- Each row: { "process": str, "as_is": [str], "to_be": [str], "impact": [str] }.
- Each list has 2-5 short bullets (≤ 100 chars each).
- No outer object. No commentary.

═══════════════════════════════════════════════════════════════════
THE ONE RULE: every as_is bullet MUST cite something specific from
the transcript — a tool name, a number, a manual workflow, a missing
capability the client actually mentioned. Generic bullets ("manual
processes", "lack of visibility", "inefficient operations") are
FORBIDDEN. If the transcript doesn't support a bullet, drop it.
═══════════════════════════════════════════════════════════════════

THIS IS WHAT GENERIC LOOKS LIKE (do NOT do this):

  ❌ as_is: ["Manual processes slow down operations",
            "Lack of real-time visibility into deliveries",
            "Inefficient route planning leads to extra costs"]
  ❌ to_be: ["Automated workflows", "End-to-end tracking", "Optimised routing"]
  ❌ impact: ["Significant time savings", "Better customer experience"]

This is generic because every bullet could apply to any logistics
client — nothing here is THIS client's pain.

═══════════════════════════════════════════════════════════════════

THIS IS WHAT GROUNDED LOOKS LIKE (do this):

Transcript snippet: "12 planners + dispatchers spending 3-4 hrs/day in
Roadnet per DC. Excel macro for holds/returns. Target trucks/day 200
→ 180-190. KPI 1300 cases/truck/day. No DC plan-time dashboards."

  ✓ as_is:
    - "12 planners + dispatchers spend 3-4 hrs/day in Roadnet per DC"
    - "Excel macro for order selection / holds / returns then re-imported"
    - "No DC plan-time tracking — managers can't diagnose plan delays"

  ✓ to_be:
    - "[routing-engine] handles 200+ constraints natively (Ramadan, school, cameras)"
    - "Native holds / returns inside the routing engine — no Excel macro"
    - "[analytics-bi] DC plan-time dashboard with drill-down on delays"

  ✓ impact:
    - "Planner effort drops sharply (3-4 hrs → ~1 hr per DC)"
    - "Trucks/day target 200 → 180-190 at same SLA window"
    - "1300 cases/truck/day KPI tracked in real time"

Every bullet cites a transcript fact. Compare row by row:
  - Numbers: "12 planners", "3-4 hrs", "200 → 180-190", "1300"
  - Tools: "Roadnet", "Excel macro"
  - Constraints: "Ramadan, school, cameras"
  - Specific capabilities: "[routing-engine]", "[analytics-bi]"

═══════════════════════════════════════════════════════════════════

WRITING DISCIPLINE:

1. Read the transcript. List 8-15 specifics (tool names, numbers,
   regions, time windows, manual workarounds, missing dashboards).

2. Group specifics into 4-7 business processes (Delivery Planning,
   Pickup, Last-Mile, Documentation, Settlement, Analytics, etc.).
   Skip processes the transcript doesn't cover.

3. For each process:
   - as_is bullets = transcript pain, lifted as close to verbatim as fits
     in ≤100 chars
   - to_be bullets = the Shipsy capability that solves it, cited as
     [capability-id], paired with a specific outcome
   - impact bullets = business outcome with numbers when the transcript
     has them; qualitative when it doesn't (don't invent numbers)

4. Order rows by buyer relevance — biggest pain first.

5. Self-check before output: would these bullets fit ANY logistics
   company? If yes, rewrite with transcript specifics or drop.

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
