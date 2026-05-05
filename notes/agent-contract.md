# Process Flow Builder Agent — Input / Output Contract

_Owner: Naval / Sharvani · Last updated: 2026-05-04_

The contract every form factor (CLI, Web UI, Slack bot) must honour. If you change this, you change all three.

## TL;DR

**Input** = a transcript + a client name. Everything else optional.
**Output** = a PPTX + a JSON + 3 PNG previews + an issues report.

That's it. The whole tool is built around this 5-line contract.

---

## Input

### Required

| Field | Type | Example |
|---|---|---|
| `transcript` | string (raw text) | "Met with DP World today. They run 24×7 container drayage out of Jebel Ali…" |
| `client_name` | string | "DP World Logistics" |

The transcript can be **messy**. Bullets, half-sentences, mid-thought edits, multiple meetings concatenated — all fine. The agent's first stage is built to clean it up. If the SE has to pre-format their notes, we've already lost.

### Optional (improves quality if provided, agent guesses otherwise)

| Field | Type | Default behaviour | When to set |
|---|---|---|---|
| `vertical_hint` | enum: `fmcg-distribution` \| `container-drayage` \| `post-and-parcel` \| `pallet-network` \| `q-commerce` \| `3pl-cross-border` \| `cold-chain` \| `other` | Inferred by Stage 1 | When SE knows it confidently — saves a guess and a token spend |
| `mode` | enum: `full` \| `flow_only` \| `mapping_only` \| `agents_only` | `full` | When regenerating one slide of a previous deck |
| `existing_json` | object (matches `schema.json`) | None | Iteration: SE edited a previous JSON and wants it re-rendered, or wants ONE section regenerated against an updated transcript |
| `regenerate_section` | enum: `process_flow` \| `process_mapping` \| `ai_use_cases` | None | With `existing_json`, only re-runs that one stage |
| `style_overrides` | object (sidebar colour, title text, etc.) | Skynet defaults | Rare — only if a client wants their brand baked in |
| `kb_filters` | object (e.g. `{"only_articles": ["routing-engine", "atlas-agent"]}`) | None | Power user — pin which KB articles the agent may consult |

### Concrete example — minimal

```json
{
  "transcript": "<paste meeting notes here>",
  "client_name": "Aljomaih (Pepsi KSA)"
}
```

### Concrete example — power user iterating

```json
{
  "transcript": "<updated transcript with new info from follow-up call>",
  "client_name": "Aljomaih (Pepsi KSA)",
  "existing_json": { "client": {...}, "process_flow": {...}, ... },
  "regenerate_section": "process_mapping"
}
```

### What the SE does NOT have to provide

- The 7-row sidebar structure
- Icon names
- Which AgentFleet agents to include
- As-is/to-be/impact bullets
- Slide titles
- File names
- Anything about Skynet template / visual style

If we ever ask for any of this, the tool has failed.

---

## Output

Every run returns a **bundle**, not a single file. Bundle layout:

```
runs/<run_id>/
├── deck.pptx                ← the deliverable for the client meeting
├── flow.json                ← the agent's curated structure
├── previews/
│   ├── slide-1.png          ← Process Flow with Shipsy
│   ├── slide-2.png          ← Process Mapping & Capability Enhancement
│   └── slide-3.png          ← AI Use Cases · AgentFleet
├── issues.md                ← what the agent guessed / wants confirmed
└── run_metadata.json        ← model, tokens, time, KB articles consulted
```

`run_id` = ULID like `01HX9F3K7QY2MZRA8GVPWS5T6N`. URL-safe, sortable, never collides.

### deck.pptx

The 3-slide deliverable. Already-styled, ready to drop into a longer deck or present as-is. **Filename pattern**: `<ClientShort>_process_flow_<YYYY-MM-DD>.pptx`.

### flow.json

The full curated structure that fed the renderer. **This is the SE's edit surface.** When they want to tweak a label, swap an icon, reorder steps — they edit this file and re-render. Schema in `.claude/skills/process-flow/schema.json`.

### previews/*.png

3 PNG renders of the 3 slides at 110 DPI. Lets the SE review the deck **without opening PowerPoint** — critical for Slack flow ("here's what it looks like, want the file?") and for the web UI thumbnail strip.

### issues.md

The piece that turns this from "AI black box" into "draft I can trust". Contains:

- **Assumptions made** — fields the agent inferred (e.g. "Inferred vertical: fmcg-distribution. Override with `vertical_hint` if wrong.")
- **Information gaps** — what the transcript didn't cover (e.g. "Service-time per customer not mentioned — assumed 1-3 hr based on hyper/super context.")
- **Low-confidence picks** — where the agent had to guess between two equally plausible options (e.g. "Picked NEXA over VERA for finance reconciliation. Both fit; revisit if dispute resolution is the bigger pain.")
- **Capabilities the agent claimed but didn't verify in KB** — anything not grounded in DevRev articles
- **Suggested follow-up questions for the next client meeting** — bonus signal for the SE

Without this file, SEs will either trust the deck blindly (bad) or audit it manually for 30 min (defeats the point).

### run_metadata.json

```json
{
  "run_id": "01HX9F3K7QY2MZRA8GVPWS5T6N",
  "user": "lakshmi.sharvani@shipsy.io",
  "client_name": "Aljomaih (Pepsi KSA)",
  "vertical": "fmcg-distribution",
  "mode": "full",
  "started_at": "2026-05-04T11:23:01Z",
  "duration_ms": 28430,
  "model": "claude-sonnet-4-20251022",
  "stages": {
    "profile":        { "input_tokens": 2104, "output_tokens": 412,  "ms": 1820 },
    "process_flow":   { "input_tokens": 6588, "output_tokens": 1840, "ms": 9120 },
    "process_mapping":{ "input_tokens": 7230, "output_tokens": 2950, "ms": 11200 },
    "ai_use_cases":   { "input_tokens": 3122, "output_tokens": 980,  "ms": 4180 },
    "validate":       { "input_tokens": 411,  "output_tokens": 87,   "ms": 720 }
  },
  "kb_articles_consulted": [
    "routing-engine", "dispatch-control-tower", "agentfleet-catalog",
    "fmcg-distribution-playbook", "settlement-finance"
  ],
  "cost_usd": 0.18
}
```

For audit, debugging, cost tracking, and the eventual self-improvement loop.

---

## End-to-end SE journey

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SE finishes client meeting, has rough notes              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SE submits via Web UI / Slack / CLI                      │
│    Input: transcript + client_name (everything else default)│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Agent runs (~30s)                                        │
│    Stage 1 → 2 → 3 → 4 → 5                                  │
│    Streams progress: "Designing process flow…"              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Bundle returned                                          │
│    SE sees 3 PNG previews + issues.md inline                │
│    Decides: ship-as-is / tweak / regenerate-section         │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
┌─────────────────────┐   ┌──────────────────────────────────┐
│ Ship                │   │ Iterate                          │
│ Download deck.pptx  │   │ Edit flow.json inline OR         │
│ Done.               │   │ Hit "Regenerate AgentFleet"      │
└─────────────────────┘   │ → goes back to step 3 with       │
                          │   existing_json + regen_section  │
                          └──────────────────────────────────┘
```

Total SE time per deck: target **< 5 minutes** (vs ~45 min today doing it by hand).

---

## Form-factor specifics

### CLI (Phase 1)

```bash
# Minimal
pf build meeting-notes.txt --client "DP World Logistics"

# With hint
pf build meeting-notes.txt --client "DP World" --vertical container-drayage

# Regenerate one section
pf rebuild runs/01HX9F3K7QY2MZRA8GVPWS5T6N --section process_mapping

# Render only (skip agent — useful when editing JSON by hand)
pf render flow.json --out deck.pptx
```

**Outputs**: writes the bundle to `./runs/<run_id>/`. Prints a summary table to stdout. Opens the PPTX automatically on macOS unless `--no-open`.

### Web UI (Phase 2)

- Single page, single form
- Streaming progress ("Stage 2 of 5: Designing process flow…")
- 3 preview images render as they're built
- "Regenerate this section" button on each preview
- Inline JSON editor (collapsed by default — power users only)
- Deck history sidebar — every past run, re-openable, re-renderable

### Slack bot (Phase 3)

```
@pf-builder build for Aljomaih
[upload transcript.txt]
```

Bot replies in thread:
1. ✅ Acknowledge ("Building deck for Aljomaih, ~30s…")
2. 3 preview images
3. issues.md as a code block
4. PPTX as a file attachment
5. Buttons: "Looks good" / "Regenerate Process Flow" / "Regenerate Mapping" / "Regenerate Agents"

---

## Failure modes (what the contract guarantees)

The agent must NEVER:
- Return a deck with a slide missing
- Return invalid JSON (Stage 5 + auto-repair guards this)
- Use icon names not in the manifest (validator catches this, repair stage fixes)
- Claim Shipsy capabilities the KB doesn't back up (issues.md flags any unsourced claim)
- Silently drop a section the user asked to regenerate
- Take more than 60s — if a stage hangs, fail fast with a partial bundle

Validator output on failure → returned as `error.md` in place of `deck.pptx`, with an explanation the SE can act on.

---

## What the contract does NOT include (yet)

Deferred to later phases:

- **Multi-deck batch** — "build decks for these 5 clients in one go" (Phase 4)
- **Deck delta** — "compare last week's Aljomaih deck to today's, highlight changes" (Phase 4)
- **Custom slide templates** — every client gets the Skynet 3-slide structure for now. Custom templates per client = future scope.
- **Inline annotation comments on slides** — the agent embedding speaker notes for the SE. Useful but not v1.

If a teammate asks for any of the above, capture as a follow-up — don't backfit into v1 contract.
