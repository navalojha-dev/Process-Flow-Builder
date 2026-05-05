---
name: process-flow
description: Generate a 3-slide Shipsy process-flow PPTX from a client meeting transcript. Reads the transcript, infers business model / mile stages / load type / geography / industry vertical, then produces a tailored deck — process-flow slide (Skynet template with icons preserved) + Our Learnings + Impact & Summary. Use when the user provides a transcript and asks for a process flow PPT, or types `/process-flow <path>`.
---

# Shipsy Process Flow Generator

Generates a tailored 3-slide deck for a Shipsy client based on a meeting / call transcript.

## When to invoke this skill

- The user uploads or references a transcript file and asks for a process flow PPT.
- The user types `/process-flow <transcript-path>` or `process-flow <transcript-path>`.
- The user explicitly asks for a Skynet-style process-flow deck for a new client.

## Output

Three slides (filename: `<client_short>_process_flow.pptx`):

1. **Process Flow with Shipsy** — the 7-row Skynet template (Order Creation → First Mile → Middle Mile → Last Mile → CX Communication → Finance → Analytics), icons preserved, labels tailored to the client's vocabulary.
2. **Process Mapping & Capability Enhancement with Shipsy** — 4-column matrix: Business Process · As Is · To-Be · Impact. 5–7 inferred process rows.
3. **AI Use Cases · AgentFleet for {Client}** — 2×3 grid of agent cards, each with agent name, tagline, transcript-grounded scenario, and a Phase tag (Now / Phase 2 / Future).

## Workflow when invoked

### 1. Locate the transcript

Resolve the path the user gave. Accept `.txt`, `.md`, `.docx`, `.vtt`, `.srt`. For `.docx`, extract text via `python3 -c "import docx; print('\n'.join(p.text for p in docx.Document('PATH').paragraphs))"` (install `python-docx` with `python3 -m pip install --user python-docx` if missing). For `.vtt`/`.srt`, strip timecodes/sequence numbers and keep speaker text.

### 2. Read the transcript

Use the `Read` tool. If it's longer than ~20K tokens, prioritize: (a) opening introductions, (b) sections where they describe their current operation, (c) any explicit pain-point statements, (d) any references to systems they use today (ERP, WMS, TMS, Sage, SAP, in-house tools), (e) discussion of geography/coverage, (f) discussion of load type (parcel/pallet/FTL/cold-chain).

### 3. Infer the structured profile

Produce a JSON object matching `schema.json` (see this directory). Inferences MUST be grounded in the transcript — do not fabricate. If a field cannot be inferred, use the most defensible default and flag it to the user. Specifically:

| Field | What to look for in transcript |
|---|---|
| `client.name` | Company name, full form |
| `client.short` | Their abbreviation / how they refer to themselves |
| `client.industry_vertical` | "we are a CEP", "pallet network", "freight forwarder", "FMCG distributor", "hyperlocal", "automotive parts", etc. |
| `client.geography` | Cities, countries, regions mentioned. Watch for "ferry connections", "GCC", "ANZ", "PAN-India", "cross-border" |
| `client.load_type` | "pallets", "parcels", "FTL/PTL", "containers", "cold chain", "DG shipments" |
| `client.business_model` | B2B / B2C / B2B2C / D2C / federated network / franchise model |
| `client.mile_stages` | Array — include only stages they actually run/care about. Common: `["first_mile","middle_mile","last_mile"]`. Add `"reverse"` if returns are emphasised. |

### 4. Tailor every step label to the client's vocabulary

Don't copy Skynet's defaults verbatim. Examples:

- A pallet network calls collections "collections" not "pickups"; uses "trunk" not "line haul"; uses "consignment notes" or "pallets" not "shipments".
- An FMCG cold-chain client adds "Temperature logging" / "Reefer compartment validation".
- A hyperlocal q-commerce client uses "rider" not "driver", "store dispatch" not "depot", and ETAs in minutes.
- A B2B freight client says "loads" not "orders", "manifests" not "labels".

Map the row content to what the client actually does. The 7-row × 5-step skeleton stays fixed (so icons line up), but each step label is the client's term for that step.

### 5. Day markers and bottom strip

Map `day_markers` to the milestones THIS client cares about. If they're a network with phased rollout, use `Phase 1 / Phase 2 / Phase 3`. If they're parcel-fast, use `Day 1 / Day 1 / Day 2`. The 5 right-side markers correspond to (in order): order_creation, first_mile, middle_mile, last_mile, analytics. The 3 bottom-strip markers are the technical/integration/implementation phases.

### 6. Learnings (3-7 bullets)

Quote or paraphrase actual pain points from the transcript. Numbers wherever possible (e.g. "60% capacity utilisation", "4-hour wait times", "20:00 planning start"). If you're forced to generalise, do so cautiously and clearly mark it.

### 7. Summary + AI Impact (3-7 + 3-6 bullets)

- **Summary** = concrete Shipsy modules / capabilities being deployed for this client. Mirror the row content: customer portal, hub ops app, driver app, BI, etc.
- **AI Impact** = punchy one-liner value statements. Tie each to a Shipsy AI agent where relevant: ASTRA (driver assist), CLARA (CX/WISMO), NEXA (settlement), VERA (dispute), ATLAS (control tower), or platform-level capabilities like address intelligence and routing.

### 8. Render

```bash
cd "/Users/shipsy/Process Flow Builder/.claude/skills/process-flow"
python3 render.py /tmp/<client>_flow.json /tmp/<client>_process_flow.pptx
```

(Save the JSON to `/tmp` for traceability — don't litter the project folder.)

### 9. Visual QA — REQUIRED

Always render to PDF/JPG and inspect:

```bash
cd /tmp && soffice --headless --convert-to pdf <out>.pptx --outdir /tmp
pdftoppm -jpeg -r 110 /tmp/<out>.pdf /tmp/qa
ls /tmp/qa-*.jpg
```

Then `Read` each JPG. Verify:
- Title shows the client's name (or "Process Flow with Shipsy")
- All 5 First Mile and 5 Middle Mile step labels are populated (no leftover Skynet defaults)
- Last Mile labels are tailored
- Day markers match what's in the JSON
- Snapshot box on slide 2 shows all 5 inferred fields without overlap
- Slide 3's two columns are balanced

If anything is off, edit the JSON and re-render. Stop after one fix-and-verify cycle.

### 10. Hand back to user

Move the final PPTX to `/Users/shipsy/Process Flow Builder/outputs/<client>_process_flow.pptx` (create that dir if it doesn't exist) and tell the user the path. Optionally show one of the QA JPGs inline.

## Files in this skill directory

| File | Purpose |
|---|---|
| `SKILL.md` | This file |
| `templates/process_flow.pptx` | Single-slide template extracted from Skynet deck (icons + layout preserved) |
| `render.py` | Reads flow JSON, opens template, substitutes text, appends Learnings + Impact slides, saves output |
| `schema.json` | JSON schema the flow must conform to |
| `samples/tpn_flow.json` | Worked example for The Pallet Network |
| `samples/tpn_output.pptx` | Reference output |

## Schema additions for slides 2 + 3

The flow JSON now needs two extra top-level fields. Use the worked
example in `samples/tpn_flow.json` as a reference for shape and tone.

### `process_mapping` — slide 2 (the matrix)

5–7 rows. Each row is one business-process area with three cell arrays
(`as_is`, `to_be`, `impact`). 3–4 bullets per cell, ≤ 90 chars each.

```jsonc
"process_mapping": [
  {
    "process": "Auto-Allocation & Planning",
    "as_is":  ["bullet", "bullet", "bullet"],
    "to_be":  ["bullet", "bullet", "bullet"],
    "impact": ["bullet", "bullet", "bullet"]
  }
]
```

**Row-naming rules**: pick rows that match THIS client's vocabulary, not
generic Skynet labels. Examples by vertical:

| Vertical | Typical row labels |
|---|---|
| Container drayage / port trucking | Booking · Resource Modelling · Auto-Allocation · Documentation Workflow · Execution & Tracking · Dispatch Visibility |
| Pallet network | Pallet Booking · Collection Ops · Hub Sortation · Trunk Tracking · Last Mile Delivery · Finance Recon · Partner Performance |
| Parcel CEP | Onboarding & Contracts · Shipment Creation · Hub Ops · Last Mile · CX & WISMO · Finance & Settlement |
| Cold-chain / FMCG | Order Capture · Cold-chain Setup · Pickup · Reefer Transit · Delivery · Temperature Audit · Reconciliation |

### `ai_use_cases` — slide 3 (the agent cards)

4–6 cards. Each card has agent name, short tagline, transcript-grounded
scenario, and a phase tag.

```jsonc
"ai_use_cases": [
  {
    "agent": "ATLAS",
    "tagline": "Control Tower Agent",
    "scenario": "≤180-char client-specific scenario",
    "phase": "Now"  // or "Phase 2" / "Future"
  }
]
```

**Agent shortlist** (pick the 6 most relevant for the client):

| Agent | Tagline | Use when transcript shows… |
|---|---|---|
| ATLAS | Control Tower Agent | exception management / dispatcher overload / SLA breaches |
| ASTRA | Driver Assist Agent | idle drivers, route deviation, driver safety, on-time issues |
| CLARA | CX / WISMO Agent | "where is my shipment", inbound calls, consignee experience |
| NEXA | Settlement Agent | invoice reconciliation, charge mismatches, billing leakage |
| VERA | Dispute Resolution Agent | claims, damage, detention, dispute cycle times |
| Address Intelligence | Geocoding + Yard Precision | address quality, geofence misses, port/yard precision |
| Routing Engine | 200+ Constraint Optimiser | manual route planning, constraint chaos, cross-border lanes |
| Driver Gamification | Performance + Loyalty | driver attrition, productivity gaps, behavioural KPIs |

**Phase rules**:
- `Now` — capability is GA, this is being deployed in Phase 1
- `Phase 2` — the buyer explicitly asked for AI later, OR the agent is recently launched (e.g., NEXA Jan 2026)
- `Future` — aspirational, mention but don't lead with it

## Module catalogue (use these names verbatim)

When writing TO-BE bullets in the matrix, refer to Shipsy modules by these canonical names so wording stays consistent across decks:

- **TMS Allocation Engine** · **Auto-Allocation Engine**
- **Asset Master** · **Driver Master / Roster**
- **Trip Object** · **Workflow Builder** · **Document Repository**
- **Customer Portal** · **Driver Mobile App** · **Hub Ops App**
- **Routing Engine** · **Address Intelligence**
- **Communication Engine** · **Customer Contracts & Invoicing**
- **Vendor Rate Cards & Payouts** · **COD / Reconciliation**
- **Control Tower (LIA)** · **Shipsy BI / Analytics**
- **Driver Gamification** · **Multi-Carrier Management** · **Integration Marketplace**

## Failure modes / edge cases

- **Transcript is too sparse** to infer (e.g. a 5-line snippet): tell the user what's missing and ask. Don't fabricate.
- **Client name missing**: ask the user, or use the file name's stem as `short` and ask.
- **Icons missing for a client-specific step**: reuse the closest Skynet icon. Don't try to replace the icon — the value is the layout consistency.
- **Long pain-point bullets wrap awkwardly on slide 2**: trim to ~120 chars per bullet; the renderer wraps but very long lines crowd the panel.
- **Customer wants more than 7 learnings or 6 AI-impact items**: schema enforces caps. Pick the strongest. Tell the user the others were dropped.

## What this skill does NOT do (yet)

- Replace the Skynet logo in the top-right of slide 1. (Future: support `--client-logo` flag.)
- Translate to non-English. (Slide content stays English.)
- Embed videos / animation. (Plain PPTX only.)
- Generate alternate flow shapes (e.g. cold-chain-specific 8-row layouts). The 7-row skeleton is fixed by the Skynet template.
