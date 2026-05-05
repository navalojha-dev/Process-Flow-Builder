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

OUTPUT FORMAT (strict — no exceptions):
- Output a single JSON array. The array contains 4 to 6 elements.
- Each element MUST be a JSON OBJECT with exactly these four string fields:
    "agent", "tagline", "scenario", "phase"
- DO NOT output a list of strings. DO NOT wrap in an outer object. DO NOT include any other text.

CONCRETE EXAMPLE of valid output (this exact shape, with your own values):
[
  {"agent": "Routing Engine", "tagline": "200+ Constraint Optimiser", "scenario": "Replaces Roadnet at 19-DC fleet scale; handles Ramadan / school / camera windows.", "phase": "Now"},
  {"agent": "ATLAS", "tagline": "Control Tower Agent", "scenario": "Tracks DC plan time end-to-end and routes delays to the responsible manager.", "phase": "Now"},
  {"agent": "Service Time AI", "tagline": "Service-Time Predictor", "scenario": "Learns 1-3 hr hyper/super dwell times from history and feeds the next routing pass.", "phase": "Phase 2"}
]

CONTENT RULES:
- Pick 4-6 agents from the catalog below. Use ONLY the agent names that appear in the catalog.
- Each `scenario` MUST mention something concrete to THIS client (their geography / load / pain / scale). Generic scenarios are worse than not picking the agent.
- `tagline` ≤ 35 chars.
- `scenario` ≤ 220 chars.
- `phase` ∈ {"Now", "Phase 2", "Future"}. Lean "Now" for routing / control-tower / address-intelligence; reserve "Future" for VERA / NEXA finance-ops use cases.

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
