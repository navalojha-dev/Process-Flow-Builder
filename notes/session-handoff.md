# Process Flow Builder — Session Handoff

_Last updated: 2026-05-04_

## What this tool is

A Claude Code **skill** (`/process-flow`) that takes a client meeting transcript and produces a 3-slide PPTX deck modelled on Shipsy's Skynet workshop deck:

1. **Process Flow with Shipsy** — 7-row sidebar (graduated navy→blue), step icons connected by solid block arrows
2. **Process Mapping & Capability Enhancement** — As-Is / To-Be / Impact matrix
3. **AI Use Cases · AgentFleet** — 2×3 grid of agent cards with phase pills

No Anthropic API key needed — the intelligence (curating rows, picking icons, writing as-is/to-be bullets) happens inside the active Claude Code session that invokes the skill. The skill itself is just a Python renderer + a SKILL.md briefing me on how to fill the JSON.

## Repo layout

```
/Users/shipsy/Process Flow Builder/
├── README.md
├── requirements.txt                 # python-pptx
├── outputs/                         # generated decks live here
│   ├── DPWorld_process_flow.pptx
│   ├── Aljomaih_process_flow.pptx           (territory + delivery combined)
│   └── Aljomaih_B2B_process_flow.pptx       (delivery-only, NEW)
├── notes/
│   └── session-handoff.md           # this file
└── .claude/skills/process-flow/
    ├── SKILL.md                     # briefing for the LLM session
    ├── schema.json                  # v2 dynamic-flow grammar
    ├── render.py                    # programmatic PPTX builder
    ├── icons/                       # 23 PNG icons + manifest.json (73 aliases)
    ├── samples/                     # tpn_flow.json reference
    └── templates/process_flow.pptx  # original Skynet extraction (NOT used at render — kept for reference)
```

## Visual grammar (locked)

- **Slide size**: 10″ × 5.625″ (16:9)
- **Sidebar**: graduated `RGBColor(0x1F,0x3A,0x5F)` (top, deep navy) → `RGBColor(0x6E,0x8C,0xB8)` (bottom, medium blue)
- **Title bar**: white background, navy 28pt bold "Process Flow with Shipsy" + Shipsy chevron mark top-right (`shipsy-logo-mark.png`, height 0.40″, x=8.85″)
- **Step arrows**: `MSO_SHAPE.RIGHT_ARROW`, height 0.16″, fill `RGBColor(0x9E,0xAE,0xC2)` — solid block arrows, NOT dashed connectors
- **No day markers** (removed)
- **No bottom strip** (Off-the-shelf / Light Custom / Custom Build — removed)
- **Slide 2**: manual rectangle grid (NOT python-pptx Table — tables auto-grow rows ignoring requested heights). Variable-height rows via `_estimate_wrapped_lines()` heuristic.
- **Slide 3**: 2×3 agent cards with phase pill in **top-right** (was bottom-left, moved to avoid scenario-text collision). Agent name auto-shrinks if long (≤8ch=18pt, ≤12ch=16pt, ≤16ch=13pt, else 11pt — handles "Address Intelligence").

## Authoring discipline (very important)

When the user supplies a transcript and asks me to build a flow:

- **Do NOT blanket-rename functional rows.** Start from Skynet's standard 7-row skeleton:
  1. Order Creation and First Mile planning
  2. First Mile Journey and Hub Activities
  3. Middle Mile Journey · Hub-to-Hub
  4. Last Mile Operations
  5. Customer Communication
  6. Finance Operations
  7. Analytics & Reporting
- Then per row apply **keep / modify / remove / add**:
  - Keep Skynet defaults that apply
  - Modify only labels where client vocabulary differs
  - Remove steps that don't apply
  - Add client-specific steps (with icon names from manifest or aliases)
- Per-row step count: **2-6 max** (wider rows lose readability)
- Per-step label: **≤ 45 chars** (multi-line via `\n` if needed)

Icons: pick from `icons/manifest.json`. 73 aliases let you say "container", "doc-check", "phone-gps", "geofence", "control-tower" instead of the canonical 23 file names. Unknown names fall back to a labeled rounded-rect.

## Decks built so far

| Client | Use case | Flow JSON | Output PPTX |
|---|---|---|---|
| DP World Logistics | Container drayage / port + cross-border | `/tmp/pf_runs/dpworld_flow.json` | `outputs/DPWorld_process_flow.pptx` |
| Aljomaih · Pepsi KSA | Combined: territory planning + day delivery | `/tmp/pf_runs/aljomaih_flow.json` | `outputs/Aljomaih_process_flow.pptx` |
| Aljomaih · Pepsi KSA | **B2B day delivery only** (NEW) | `/tmp/pf_runs/aljomaih_b2b_flow.json` | `outputs/Aljomaih_B2B_process_flow.pptx` |
| TPN (reference) | Pallet network | `samples/tpn_flow.json` | `outputs/TPN_process_flow.pptx` |

## Key facts captured for Aljomaih (Pepsi KSA)

- 19 DCs, ~450 trucks across 2 entities (300+150)
- 4-bay / 6-bay / 10-bay (mostly 10-bay)
- 12 planners + dispatchers, 250 + 120 territories
- Supermarket receiving 06:30-12:30, hyper / super service time 1-3 hr
- Wave dispatch 5 AM / 7 AM
- Planner effort today: 3-4 hrs/day per DC in Roadnet
- KPI: 1300 cases/truck/day; target trucks/day reduction 200 → 180-190
- Pain: cloud desire, integrations to Oracle EBS / CRM / ISIL / Salesforce automation, master data trapped in Roadnet, dynamic routing limits, KSA road restrictions (Ramadan / school zones / camera fines), Excel-macro workflow for holds/returns, no DC plan-time dashboards, MoT KSA waybill portal integration

## B2B-only Aljomaih flow (just built)

The combined flow merged territory planning (pre-seller route building) with day delivery. The B2B-only flow strips territory work and focuses on the order-to-store pipeline:

```
Order Ingestion · Pre-Sales to Plan
  Supermarket / Hyper Orders → Pre-Sales captured in Oracle EBS → Next-day order pool synced to Shipsy

Routing & Plan Generation
  200+ constraints → Truck + bay-capacity matching → Holds / returns / order selection → Trucks/day optimised

Warehouse Picking & Loading
  Pick list per route → Loading per route + bay sequence → MoT waybill auto-generated → Wave dispatch (5 AM / 7 AM)

Last Mile · Delivery to Store
  Driver receives trip → Navigation → Service time at hyper/super (1-3 hr) → ePOD + cases delivered → Trip data sync to Oracle EBS

Store Communication & Slot Adherence
  Stage-wise comms → Live tracking + ETA → Receiving window 06:30-12:30 adherence → Geofence-based delivery validation

Finance Operations
  Truck operating cost tracking → Sub-contractor rate contracts → Plan vs actual cost reconciliation

Analytics & Reporting
  Cases/truck/day (KPI 1300) → DC plan-time tracking + drill-down → Driver / dispatcher / planner performance
```

Visual QA: passed (3-slide PDF rendered, all rows fit, arrows clean, title doesn't wrap).

## Known issues / pending work

- **SKILL.md update** is `in_progress` — needs v2 grammar rules + icon catalog + per-vertical row recipes documented inside SKILL.md so a fresh Claude session knows the discipline without reading this handoff.
- **Team distribution**: not yet pushed to a git repo. Proposed earlier but not executed. Need:
  - `setup.sh` (one-time deps install + sample run)
  - `QUICKSTART.md` for teammates
  - Repo location TBD (Shipsy GitHub org?)
- **`/Users/shipsy/.git`**: home dir was accidentally `git init`-ed before this session. Cleaning it up is a side-task; doesn't block anything but should not be left.
- **Icon edge cases**: some labels still wrap to 2 lines in the bullet/process-mapping slide for very long sentences. Heuristic in `_estimate_wrapped_lines()` works for most cases; if a future deck has very long bullets, may need to bump the chars-per-line estimate.

## How to render a new deck (mechanical recipe)

```bash
cd "/Users/shipsy/Process Flow Builder"
python3 .claude/skills/process-flow/render.py <flow.json> outputs/<Client>_process_flow.pptx
# visual QA:
soffice --headless --convert-to pdf outputs/<Client>_process_flow.pptx --outdir /tmp/pf_runs/
pdftoppm -r 110 /tmp/pf_runs/<Client>_process_flow.pdf /tmp/pf_runs/<client> -png
```

Then `Read` the three PNGs to spot-check layout.

## Session conversation root

Full transcript (pre-compaction): `/Users/shipsy/.claude/projects/-Users-shipsy-Process-Flow-Builder/5309e636-7c41-4562-9e5c-c2bdef6a2864.jsonl`
