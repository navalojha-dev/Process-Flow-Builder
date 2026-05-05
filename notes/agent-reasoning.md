# How the Agent Reasons — Transcript → Deck

_Last updated: 2026-05-04_

This is the "show your work" document. When the agent produces a bad deck,
this doc tells you which **pass** failed and how to fix it.

The agent doesn't read a transcript top-to-bottom and write a deck. It makes
**5 passes**, each looking for a different kind of signal. The output of each
pass feeds a different part of the deck.

```
PASS 1 · Profile facts          ──→ client.{name, vertical, geography, scale}
PASS 2 · Current-stack signals  ──→ as-is bullets (slide 2)
PASS 3 · Pain + numeric KPIs    ──→ to-be / impact bullets (slide 2)
PASS 4 · Operational constraints──→ row design + step labels (slide 1)
PASS 5 · "AI/automation" wants  ──→ AgentFleet picks + phasing (slide 3)
```

## Pass-by-pass — what each is looking for

### Pass 1 — Profile facts

**Looking for:** proper nouns, geography names, fleet size numbers, business model verbs ("we deliver to", "we ship from", "B2B" / "B2C").

**Produces:** the `client` block.

**Tell-tale failure:** wrong vertical, generic geography string. Almost always
because the transcript mentioned the company name but didn't describe what they
*do*. Fix: pass `--vertical` explicitly.

### Pass 2 — Current-stack signals

**Looking for:** tool names (Roadnet, SAP, Oracle EBS, WhatsApp, Excel),
verbs of process pain ("manual", "by phone", "in spreadsheets", "on paper"),
the word "today".

**Produces:** `as-is` bullets in the `process_mapping` matrix.

**Tell-tale failure:** as-is bullets are vague ("they have manual processes").
Means the transcript was thin on tool names. Ask the SE to add 2-3 lines about
what tools the client uses today.

### Pass 3 — Numeric KPIs and quantifiers

**Looking for:** `\d+%`, `\d+ hrs`, target metrics, scale numbers, words like
"target", "reduce", "improve", "by Q3".

**Produces:** `impact` bullets (quantitative when possible) and the framing of
to-be promises.

**Tell-tale failure:** impact bullets are all qualitative ("better visibility",
"faster planning"). Means the transcript had no numbers. Either add them, or
accept that impact is qualitative for this client and revise expectations
with the buyer.

### Pass 4 — Operational constraints

**Looking for:** time-window constraints ("06:30-12:30"), regulatory
constraints (Ramadan / customs / DOT), capacity constraints ("4/6/10-bay"),
geographic constraints (cross-border, urban congestion), volume constraints
(cases/day, parcels/hour).

**Produces:** the row structure for slide 1 (keep / modify / remove / add
against Skynet's 7-row skeleton) AND the step labels within each row.

**Tell-tale failure:** generic slide 1 ("Order → Pickup → Delivery"). The
biggest signal that the agent went generic. Caused by: (a) constraints
not in the transcript, (b) constraints not in the vertical playbook in
`catalog.py`. Fix: enrich one or the other.

### Pass 5 — "AI / automation" explicit asks

**Looking for:** the words "AI", "automate", "machine learning", "smart",
"predict", "intelligent", explicit asks for any of {control tower, settlement,
dispute resolution, predictive ETA, geocoding, route optimization}.

**Produces:** the AgentFleet picks on slide 3 + their phase.

**Tell-tale failure:** all agents are "Now" (over-eager) or all are "Future"
(under-confident). Both are wrong. Honest phasing means: 2-3 "Now" (the
table-stakes), 1-2 "Phase 2" (next quarter), 1-2 "Future" (strategic). If the
transcript bucketed something explicitly as "AI we want eventually", that's
"Phase 2" — don't promote it to "Now".

## Worked example — Aljomaih (Pepsi KSA) transcript

### Pass 1 extractions

| Transcript line | Extracted |
|---|---|
| "Aljomaih (Pepsi KSA)" | name = "Aljomaih · Pepsi KSA" |
| "19 DCs, ~300+~150 trucks (two entities)" | scale = ~450 trucks across 2 entities |
| "Pre-sellers visit, capture orders... → next-day delivery" | vertical = `fmcg-distribution` |
| "supermarket receiving 06:30-12:30" | mile_stages = `["middle_mile", "last_mile"]` |
| "Cases + Pallets · 4/6/10-bay" | load_type = "Cases + Pallets · 4/6/10-bay trucks" |

### Pass 2 extractions (as-is bullets)

| Signal | as-is bullet |
|---|---|
| "12 planners + dispatchers spending 3-4 hrs/day in Roadnet" | "12 planners + dispatchers spending 3-4 hrs/day in Roadnet per DC" |
| "Excel macro for order selection / holds / returns" | "Excel macro for order selection / holds / returns, then re-imported" |
| "Pre-sellers → Oracle EBS → Roadnet → planners route" | "Trips hop from Roadnet → Oracle EBS → Salesforce handhelds" |
| "no DC plan-time dashboards" | "No DC plan-time tracking — managers can't see why a plan was delayed" |

### Pass 3 extractions (numeric impact)

| Signal | Used as |
|---|---|
| "KPI: 1300 cases/truck/day" | Analytics row label |
| "target trucks/day 200 → 180-190" | impact: "Trucks/day reduce (target 200 → 180-190) at same SLA window" |
| "~3-4 hrs/planner/day" | impact: "Planner effort drops sharply (3-4 hrs → ~1 hr per DC)" |
| "1-3hr service time at hyper/super" | step label + Service Time AI scenario |

### Pass 4 extractions (row design)

| Constraint signal | Row decision |
|---|---|
| "road restrictions: Ramadan / school zones / camera locations" | MODIFY Row 2 step label: "200+ constraints (Ramadan / school / cameras)" |
| "supermarket receiving 06:30-12:30" | MODIFY Row 5 to "Store Communication & Slot Adherence" |
| "wave dispatch 5 AM / 7 AM" | ADD step: "Wave dispatch (5 AM / 7 AM)" |
| "MoT KSA waybill portal integration" | ADD step: "MoT waybill auto-generated" |
| "4/6/10-bay (mostly 10-bay)" | MODIFY Row 2 step: "Truck + bay-capacity matching" |
| _no first-mile pickup mentioned_ | REMOVE Skynet's "First Mile Journey" row |
| _warehouse picking is its own pain_ | ADD "Warehouse Picking & Loading" row |

### Pass 5 extractions (agent picks)

| Signal | Agent · Phase | Why this phase |
|---|---|---|
| "200+ constraints / Ramadan / school / cameras / bay capacity" | **Routing Engine** · Now | Table-stakes — without this they can't replace Roadnet |
| "no DC plan-time dashboards" | **ATLAS** · Now | Headline pain in the transcript |
| "AI: historical-data service time prediction" | **Service Time AI** · Phase 2 | They explicitly bucketed it as "AI" → not core, but on roadmap |
| "370+ territories, new customers" | **Address Intelligence** · Now | Geofence reliability scales with customer base |
| _no driver-side pain mentioned_ | **ASTRA** · Phase 2 | Don't promote to Now — be honest |
| _no settlement / dispute pain_ | **NEXA** · Future | Restraint — don't oversell |

### Final structure

```
flow.json
├── client                                      [from Pass 1]
├── process_flow                                [from Pass 4]
│     rows[]: 7 entries, all FMCG-shaped
├── process_mapping                             [from Passes 2 + 3]
│     6 rows, as-is grounded, impact quantitative where possible
└── ai_use_cases                                [from Pass 5]
      6 agents, phased honestly: 3 Now / 2 Phase 2 / 1 Future
```

## Mapping to the CLI

| Pass | CLI stage | File |
|---|---|---|
| 1 | Profile | `pf_builder/stages/profile.py` |
| 4 (rows) | Process Flow | `pf_builder/stages/process_flow.py` |
| 2 + 3 (matrix) | Process Mapping | `pf_builder/stages/process_mapping.py` |
| 5 (agents) | AI Use Cases | `pf_builder/stages/ai_use_cases.py` |
| validation | Validate | `pf_builder/stages/validate.py` |

Each stage's system prompt encodes the corresponding pass's discipline. That's
why the pipeline works without a human in the loop — the discipline is portable.

## Debugging guide — when a deck looks wrong

| Symptom | Failed pass | Fix |
|---|---|---|
| Generic slide 1 ("Order → Pickup → Delivery") | Pass 4 | Enrich `catalog.py` `verticals/<vertical>` with row hints, OR pass `--vertical` |
| Vague as-is bullets ("manual processes") | Pass 2 | Ask SE to add 2-3 lines about current tools |
| Vague impact bullets ("better visibility") | Pass 3 | Ask SE to add numbers, or accept qualitative |
| All agents "Now" or all "Future" | Pass 5 | Tighten agent `fit:` keywords in `catalog.py` |
| Wrong vertical inferred | Pass 1 | Pass `--vertical` explicitly |
| Agent invented capability not in catalog | Pass 5 | Stage 5 (validate) catches this — repair loop fixes |

## What's NOT in this reasoning model (yet)

- **Cross-pass consistency** — sometimes Pass 4 picks a row that Pass 5 ought to
  produce an agent for, but Pass 5 doesn't see it. Future work: a final
  cross-check pass that validates "every major pain has at least one as-is
  bullet AND one agent".
- **Industry-specific pre-passes** — for very specialised verticals (cold chain,
  hazmat) the standard 5 passes might miss compliance signals. Add a Pass 0
  "regulatory scan" if/when those clients show up.
- **Multi-meeting transcripts** — currently the agent treats one transcript as
  one input. If you concatenate 3 meetings the inputs sometimes contradict.
  Future: a Pass 0 "deduplicate / reconcile" step.
