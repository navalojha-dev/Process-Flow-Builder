"""Stage 4 — AgentFleet curation.

Picks 4-6 agents from the catalog that fit this client, writes
client-specific tagline + scenario for each, and assigns a phase
(Now / Phase 2 / Future).
"""
from __future__ import annotations

import json

from ..kb.catalog import agentfleet_for_prompt
from ..llm import StageResult, ask_for_json

SYSTEM = """You curate the AgentFleet card grid for slide 3 of a Shipsy client deck.

Output ONLY a JSON array inside a fenced ```json block. After the block you may write 1-5 lines of "notes:" — one per line — explaining picks the SE might want to revisit.

RULES:
- Pick 4-6 agents from the catalog. Don't add agents that aren't in the catalog.
- Each agent's `scenario` MUST mention something concrete to THIS client (their geography / load / pain / scale). Generic scenarios are worse than not picking the agent.
- `tagline` ≤ 35 chars.
- `scenario` ≤ 220 chars.
- `phase`: "Now" (table-stakes / immediate value), "Phase 2" (next quarter), "Future" (strategic). Lean toward "Now" for routing/control-tower/address-intelligence; reserve "Future" for VERA / NEXA-style finance ops.

OUTPUT JSON SHAPE:
[
  {
    "agent":    "<name from catalog>",
    "tagline":  "<≤35 char>",
    "scenario": "<≤220 char, concrete to this client>",
    "phase":    "Now" | "Phase 2" | "Future"
  }
]

AGENTFLEET_PLACEHOLDER
"""

USER_TEMPLATE = """CLIENT PROFILE:
{profile_json}

PROCESS FLOW:
{flow_json}

PROCESS MAPPING MATRIX:
{mapping_json}

TRANSCRIPT (for context):
<<<
{transcript}
>>>

Pick 4-6 agents. Make each scenario concrete to this client."""


def run(
    *,
    profile: dict,
    process_flow: dict,
    process_mapping: list,
    transcript: str,
) -> StageResult:
    system = SYSTEM.replace("AGENTFLEET_PLACEHOLDER", agentfleet_for_prompt())
    user = USER_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2),
        flow_json=json.dumps(process_flow, indent=2),
        mapping_json=json.dumps(process_mapping, indent=2),
        transcript=transcript.strip(),
    )
    return ask_for_json(system=system, user=user, max_tokens=4000)
