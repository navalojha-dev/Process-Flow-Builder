"""Stage 2 — Process Flow design.

The most important stage. Takes the client profile + transcript and
designs the row-and-step structure for slide 1.

The discipline below is the difference between a generic-looking deck
and one that visibly reflects this client's actual operation. Weaker
models (Gemini Flash) tend to default to generic Skynet steps unless
the prompt aggressively forbids it — which is what this prompt does.
"""
from __future__ import annotations

import json

from ..kb.catalog import vertical_for_prompt
from ..kb.icons import catalog_for_prompt
from ..llm import StageResult, ask_for_json

SYSTEM = """You design the slide-1 process flow for a Shipsy client deck.

OUTPUT FORMAT (strict):
- Output a single JSON object. No commentary. No markdown fences.
- Top-level keys: "title" (string), "rows" (array of 4-7 row objects).
- Each row: { "name": string, "steps": array of 2-6 step objects }.
- Each step: { "label": string ≤ 45 chars, "icon": canonical icon name or alias }.

═══════════════════════════════════════════════════════════════════
THE ONE RULE: every step label MUST cite something specific from the
transcript — a tool name, a number, a region, a time window, a workflow,
a constraint. Generic verbs ("process order", "allocate driver", "track
delivery") are FORBIDDEN. If you cannot tie a step to a transcript
specific, drop the step.
═══════════════════════════════════════════════════════════════════

THIS IS WHAT GENERIC LOOKS LIKE (do NOT do this):

  ❌ Row: "Order Creation"
       Steps: [
         "Customer creates order",
         "Order validated",
         "Order sent to dispatch"
       ]

  ❌ Row: "Last Mile Operations"
       Steps: [
         "Driver allocated",
         "Route planned",
         "Delivery completed",
         "Status updated"
       ]

This is generic because nothing in those step labels could only apply
to this client. Reverse it: read the transcript first, find specifics,
then write step labels around them.

═══════════════════════════════════════════════════════════════════

THIS IS WHAT GROUNDED LOOKS LIKE (do this):

Example A — FMCG transcript mentions: "Pre-sellers visit, capture
orders in handhelds, sync to Oracle EBS. 12 planners + dispatchers
spending 3-4 hrs/day in Roadnet. Wave dispatch 5 AM / 7 AM. Receiving
06:30-12:30. Cases / pallets, 4/6/10-bay trucks, mostly 10-bay. Excel
macro for holds/returns. Ramadan / school zones / camera fines."

  ✓ Row: "Order Ingestion · Pre-Sales to Plan"
       Steps: [
         "Pre-sales captured in Oracle EBS",
         "Next-day order pool synced to Shipsy",
         "Holds / returns selected (no Excel macro)"
       ]

  ✓ Row: "Routing & Plan Generation"
       Steps: [
         "200+ constraints (Ramadan / school / cameras)",
         "Truck + bay matching (4 / 6 / 10-bay)",
         "Wave dispatch 5 AM / 7 AM"
       ]

  ✓ Row: "Last Mile · Delivery to Store"
       Steps: [
         "Receiving window 06:30-12:30 adherence",
         "Hyper / super service time (1-3 hr)",
         "ePOD + cases delivered captured"
       ]

Every label cites a transcript fact: "Oracle EBS", "Excel macro",
"4/6/10-bay", "Ramadan/school/cameras", "5 AM / 7 AM", "06:30-12:30".

Example B — Container drayage transcript mentions: "Bookings via
WhatsApp/email. CRO tokens + EIRs as paper. Cross-border to Oman, KSA.
No telematics. Truck-head + trailer + genset combos. 24×7 ops."

  ✓ Row: "Booking & Order Mgmt"
       Steps: [
         "Email / WhatsApp bookings ingested via UI + API",
         "Movement type tagged: port↔port, port↔WH, GCC cross-border",
         "Asset combo (head + trailer + genset) auto-validated"
       ]

  ✓ Row: "Documentation Workflow"
       Steps: [
         "CRO tokens + EIR uploaded against trip ID",
         "Cross-border permits + driver visas verified",
         "Gate pass shown in driver app at checkpoint"
       ]

═══════════════════════════════════════════════════════════════════

DESIGN PROCESS (do this in order):

STEP 1 — Read the transcript and list 8-15 specifics:
  - Tool / system names mentioned (Roadnet, Oracle EBS, Salesforce,
    WhatsApp, Excel, ISIL, ERP, MoT portal, etc.)
  - Numbers: trucks, planners, hours/day, KPIs, cases/day, RPM, etc.
  - Regions / countries / cities
  - Time windows (receiving hours, dispatch waves, SLA windows)
  - Constraints (Ramadan, school zones, camera fines, cross-border,
    customs, capacity rules)
  - Manual workarounds the transcript flags as pain
  - Asset / vehicle / load specifics

STEP 2 — Start from Skynet's standard 7-row skeleton:
   1. Order Creation and First Mile planning
   2. First Mile Journey and Hub Activities
   3. Middle Mile Journey · Hub-to-Hub
   4. Last Mile Operations
   5. Customer Communication
   6. Finance Operations
   7. Analytics & Reporting

STEP 3 — Apply KEEP / MODIFY / REMOVE / ADD per row:
  - KEEP rows that genuinely apply.
  - MODIFY a row name ONLY when client vocabulary differs AND the
    change carries information ("Last Mile · Delivery to Store" for
    FMCG; "Cross-Border Transit" for drayage).
  - REMOVE rows that don't apply (B2B day-delivery has no first-mile
    pickup; container drayage has no warehouse picking).
  - ADD client-specific rows when the skeleton misses something
    material that came up multiple times in the transcript.

STEP 4 — Write step labels using your Step-1 specifics. Every label
must cite at least one specific. If you have a label that could apply
to ANY logistics client, rewrite it to include a transcript fact, or
drop it.

STEP 5 — Self-check before output:
  - Could a competitor's deck use this exact step label? If yes, it's
    too generic — rewrite it.
  - Are there at least 3 distinct transcript specifics referenced
    across the whole flow? If not, the flow is too generic.
  - Are row names client-shaped (FMCG / drayage / parcel) or skeleton-
    shaped? Skeleton-shaped is OK for some rows but not all 7.

OUTPUT JSON SHAPE:
{
  "title": "Process Flow with Shipsy",
  "rows": [
    { "name": "Order Ingestion · Pre-Sales to Plan",
      "steps": [
        { "label": "Pre-sales captured in Oracle EBS", "icon": "pickup-check" },
        { "label": "Next-day order pool synced to Shipsy", "icon": "erp-sync" }
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

Design the process flow.

Before you output the JSON, internally do this (do not include in your output):
  1. List 8-15 SPECIFICS from the transcript (tools, numbers, regions, time windows, constraints, pain points).
  2. Decide the 4-7 rows by applying KEEP / MODIFY / REMOVE / ADD against the standard skeleton.
  3. Write each step label so it CITES at least one transcript specific.
  4. Self-check: would this step label fit any logistics company? If yes, rewrite it.

Then output the JSON object."""


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
