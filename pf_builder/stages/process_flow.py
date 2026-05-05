"""Stage 2 — Process Flow design.

The most important stage. Takes the client profile + transcript and
designs the row-and-step structure for slide 1.

Discipline: start from Skynet's standard 7-row skeleton, apply
keep / modify / remove / add per row. Don't blanket-rename rows. Each
row 2-6 steps. Step labels ≤ 45 chars. Icons must come from the
manifest (canonical or alias).
"""
from __future__ import annotations

import json

from ..kb.catalog import vertical_for_prompt
from ..kb.icons import catalog_for_prompt
from ..llm import StageResult, ask_for_json

SYSTEM = """You design the slide-1 process flow for a Shipsy client deck.

You output ONLY a JSON object inside a fenced ```json block. After the block you may write 1-5 lines of "design notes:" — one per line — explaining row choices the transcript didn't directly cover.

DESIGN DISCIPLINE (this is the difference between a good deck and a generic one):

1. Start from Skynet's standard 7-row skeleton:
   1. Order Creation and First Mile planning
   2. First Mile Journey and Hub Activities
   3. Middle Mile Journey · Hub-to-Hub
   4. Last Mile Operations
   5. Customer Communication
   6. Finance Operations
   7. Analytics & Reporting

2. For each row apply KEEP / MODIFY / REMOVE / ADD against the transcript:
   - KEEP rows that genuinely apply to this client.
   - MODIFY a row name only when client vocabulary differs (e.g. "Last Mile · Delivery to Store" instead of generic "Last Mile Operations" — but only if the change carries information).
   - REMOVE rows that don't apply (a B2B day-delivery client doesn't need Middle Mile Journey).
   - ADD client-specific rows when the standard skeleton misses something material (e.g. "Warehouse Picking & Loading" for FMCG day-delivery).

3. Steps inside a row:
   - 2-6 steps, left-to-right, in chronological order.
   - Label ≤ 45 chars. Multi-line labels via \\n allowed but rare.
   - Each step needs an icon from the manifest (canonical or alias). Don't invent icon names.

4. The final flow has 4-7 rows total. Don't pad — fewer crisp rows beat more generic ones.

OUTPUT JSON SHAPE:
{
  "title": "Process Flow with Shipsy",
  "rows": [
    {
      "name": "<row name>",
      "steps": [
        { "label": "<≤45 char>", "icon": "<icon-name from manifest>" }
      ]
    }
  ]
}

ICONS_CATALOG_PLACEHOLDER

VERTICAL_PLAYBOOK_PLACEHOLDER
"""

USER_TEMPLATE = """CLIENT PROFILE:
{profile_json}

TRANSCRIPT:
<<<
{transcript}
>>>

Design the process flow. 4-7 rows. Use the keep/modify/remove/add discipline."""


def run(
    *,
    profile: dict,
    transcript: str,
) -> StageResult:
    system = (
        SYSTEM
        .replace("ICONS_CATALOG_PLACEHOLDER", catalog_for_prompt())
        .replace(
            "VERTICAL_PLAYBOOK_PLACEHOLDER",
            vertical_for_prompt(profile.get("vertical", "other")),
        )
    )
    user = USER_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2),
        transcript=transcript.strip(),
    )
    return ask_for_json(system=system, user=user, max_tokens=6000)
