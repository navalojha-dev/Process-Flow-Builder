# Process Flow Builder Agent — Architecture & Plan

_Owner: Naval / Sharvani · Last updated: 2026-05-04_

## 1. Goal restated

Today: I (Claude inside Naval's CC session) read a transcript, hand-curate JSON, run `render.py` → PPTX. Works for one user.

Target: any Shipsy teammate (pre-sales, SE, AE) can paste a meeting transcript and get back a Skynet-styled 3-slide deck for their client — without needing CC, Python, or knowledge of the JSON grammar. They should also be able to **iterate**: tweak a row, regenerate one slide, refine bullets.

## 2. The hard part is NOT the renderer

```
┌────────────────────┬───────────────────────────────────┐
│ Stage              │ Status                            │
├────────────────────┼───────────────────────────────────┤
│ PPTX rendering     │ ✅ Solved (render.py, deterministic) │
│ Visual style       │ ✅ Locked (sidebar / arrows / cards) │
│ Schema             │ ✅ v2 grammar in schema.json         │
│ Agent intelligence │ ❌ Lives in my head right now        │
│ Distribution       │ ❌ Skill = single user                │
│ Iteration / edit   │ ❌ No UI, no re-render loop           │
│ Observability      │ ❌ No telemetry, no deck history      │
└────────────────────┴───────────────────────────────────┘
```

The brain — "transcript → curated rows + steps + icons + as-is bullets + AI agent picks following the keep/modify/remove/add discipline" — is the part to externalise. Renderer is a library you call at the end.

## 3. Architecture (target state)

```
┌──────────────────────────────────────────────────────────┐
│  Teammate                                                │
│  Web UI  │  Slack /pf  │  CLI (pf build transcript.md)   │
└────────┬─────────────────────────────────────────────────┘
         │ POST /build  { transcript, client_hint? }
         ▼
┌──────────────────────────────────────────────────────────┐
│  API Gateway   — Shipsy SSO, rate limit, audit log       │
└────────┬─────────────────────────────────────────────────┘
         ▼
┌──────────────────────────────────────────────────────────┐
│  Agent Orchestrator (Python / FastAPI)                   │
│                                                          │
│  Stage 1 · Profile Extraction                            │
│     → Anthropic API (Sonnet) · structured output         │
│     → returns client.{name, vertical, geography, ...}    │
│                                                          │
│  Stage 2 · Process Flow Design                           │
│     tools available to the agent:                        │
│       • list_icons()          (manifest + aliases)       │
│       • list_skynet_defaults()                           │
│       • list_vertical_recipe(vertical)                   │
│     → returns rows[] with steps[] (4-7 rows)             │
│                                                          │
│  Stage 3 · As-Is / To-Be / Impact Matrix                 │
│     tools:                                               │
│       • search_capabilities(query)  (Shipsy modules KB)  │
│     → returns process_mapping[] (4-7 rows)               │
│                                                          │
│  Stage 4 · AgentFleet Curation                           │
│     tools:                                               │
│       • list_agents()  (NEXA, ATLAS, ASTRA, VERA, ...)   │
│     → returns ai_use_cases[] (4-6 agents, phased)        │
│                                                          │
│  Stage 5 · Schema Validate + Auto-Repair                 │
│     → if invalid: feed errors back to agent, retry once  │
└────────┬─────────────────────────────────────────────────┘
         │ flow.json
         ▼
┌──────────────────────────────────────────────────────────┐
│  Renderer Service  — wraps render.py                     │
│  POST /render { flow_json } → deck.pptx + 3 PNG previews │
└────────┬─────────────────────────────────────────────────┘
         ▼
┌──────────────────────────────────────────────────────────┐
│  Storage                                                 │
│    • S3 / GCS bucket for PPTX + previews                 │
│    • Postgres: { run_id, user, transcript, json,         │
│                  pptx_url, created_at, edits[] }         │
└──────────────────────────────────────────────────────────┘
         ▲
         │ "regenerate row 3 only" / "make bullets sharper" / inline JSON edit
         │
┌──────────────────────────────────────────────────────────┐
│  Edit & Iterate Loop                                     │
│    • UI shows the 3 slide previews + the JSON            │
│    • per-section "Regenerate" buttons → calls one stage  │
│    • inline JSON edit → re-render only                   │
└──────────────────────────────────────────────────────────┘
```

### Why this shape

**Multi-stage agent vs one-shot**: I tried the "one big prompt" model in my head and it produces mediocre middle rows because the model is juggling profile + flow + matrix + agents at once. Separate stages = each prompt is small, focused, and individually testable. Cost goes up ~3× but a deck is rendered once and reused — pennies vs the SE's hour.

**Tools, not RAG soup**: the agent needs surgical access to specific catalogs (icons, agents, capabilities). Tool-calling beats stuffing all of it into the system prompt — keeps tokens down and the agent can pull more depth on demand.

**Validate + repair**: schema.json is the contract. If the agent returns invalid JSON (wrong icon name, > 6 steps in a row, missing required field), the orchestrator hands the validation error back and asks for a fix. Bounds the failure mode.

**Renderer stays dumb**: keep render.py side-effect-free. It takes JSON → PPTX. Don't let LLM output reach into rendering logic. Easier to test, easier to swap.

## 4. Knowledge base (what the agent reads)

This is the work that pays back forever. Get it right once.

```
kb/
├── skill_brief.md              # the keep/modify/remove/add discipline,
│                               # row count rules, label length caps
├── icons/manifest.json         # already exists (23 icons + 73 aliases)
├── agentfleet.json             # full AgentFleet catalog
│                               #   { agent, tagline, capabilities,
│                               #     when_to_pick, sample_scenarios }
├── capabilities/               # Shipsy modules — searchable
│   ├── routing-engine.md
│   ├── dispatch-control-tower.md
│   ├── driver-app-epod.md
│   ├── settlement-finance.md
│   ├── customer-comms.md
│   └── analytics-bi.md
├── verticals/                  # per-vertical recipes
│   ├── fmcg-distribution.md           # Aljomaih flavour
│   ├── container-drayage.md           # DPWorld flavour
│   ├── post-and-parcel.md             # Skynet flavour
│   ├── pallet-network.md              # TPN flavour
│   ├── q-commerce.md
│   ├── 3pl-cross-border.md
│   └── cold-chain.md
└── reference_decks/            # few-shot examples (already have 4)
    ├── tpn_flow.json
    ├── dpworld_flow.json
    ├── aljomaih_flow.json
    └── aljomaih_b2b_flow.json
```

Each `verticals/*.md` should be a one-pager:
- Default 7-row skeleton tweaks
- Common pain themes (what to listen for in the transcript)
- Typical AgentFleet picks
- 2-3 sample step labels per row

This file is what makes the agent _better than me_ over time. Today the discipline lives in my head; tomorrow it's in markdown your team can edit.

## 5. Phased plan

### Phase 0 — Tighten what exists (this week, ~1 day)

- Update `SKILL.md` with v2 grammar rules + icon catalog + per-vertical recipes (carryover from previous session)
- Write `setup.sh` (deps install, sample run, sanity check)
- Write `QUICKSTART.md` (for now: how a teammate clones + runs locally as a CC skill)
- Push to a Shipsy GitHub repo (private)

This unblocks 2-3 power users who already have CC, while you build Phase 1.

### Phase 1 — CLI + shared API key (1-2 weeks)

```bash
$ pf build meeting-notes.txt --client "DP World" --vertical container-drayage
✓ Profile extracted
✓ Process flow designed (5 rows, 24 steps)
✓ As-Is/To-Be/Impact matrix written (6 rows)
✓ AgentFleet curated (5 agents)
✓ Rendered → outputs/DPWorld_2026-05-04.pptx
✓ Preview → /tmp/pf_runs/dpworld-{1,2,3}.png
```

- Single Python package `shipsy-pf-builder` (pip-installable from internal index)
- Reads `ANTHROPIC_API_KEY` from env (one shared key billed to a Shipsy cost-centre)
- Same renderer (render.py) — wrapped behind the orchestrator
- CLI flags: `--client`, `--vertical`, `--regenerate-section`, `--from-json`
- Output: PPTX + JSON + 3 preview PNGs side-by-side
- Logs every run to a JSONL audit file (`~/.pf-builder/runs.jsonl`)

**Tech**: Python 3.11, `anthropic` SDK, `python-pptx`, `click` for CLI. Nothing exotic.

**Why CLI before web UI**: you can hand it to 5 SEs in a day, learn from real usage, then build UI. Jumping to web first usually ships the wrong UX.

### Phase 2 — Web UI (3-4 weeks)

- Next.js / FastAPI backend (or pure FastAPI + HTMX if team is small)
- SSO via Shipsy Google Workspace
- Single-page form: paste transcript → see live progress → preview slides → download PPTX
- Per-section "Regenerate" buttons (calls one stage of the orchestrator, not all)
- Inline JSON editor for power users (Monaco / CodeMirror)
- Deck history per user (Postgres) — re-open and re-render any past deck
- S3 / GCS for artifact storage

**Why now**: most teammates won't touch a CLI. UI is the production form factor.

### Phase 3 — Slack bot (optional, 1 week if Phase 2 is solid)

```
@pf-builder build deck for Aljomaih
[upload transcript.txt]
→ bot replies with PPTX in DM after ~30s
```

- Wraps the same backend
- Best for SEs who live in Slack during client cycles

### Phase 4 — Self-improvement loop (long horizon)

- Track which decks SEs actually presented (vs threw away)
- Capture edits SEs made post-generation (diff JSON before/after)
- Use those as fine-tuning data or in-context examples
- Eventually: the agent learns Shipsy's house style without me re-telling it

## 6. Tech choices (recommended)

| Layer | Pick | Why |
|---|---|---|
| Language | Python 3.11 | render.py already there, anthropic SDK first-class |
| LLM | Claude Sonnet 4.x via Anthropic API | quality / cost sweet spot; same model behind CC |
| Orchestration | Plain Python + `anthropic` tool use | no LangChain — keeps stack debuggable |
| API | FastAPI | async, OpenAPI for free, easy to add Slack adapter |
| Frontend | Next.js or HTMX + FastAPI | depends on team JS appetite |
| Auth | Google Workspace SSO via NextAuth or Authlib | already what Shipsy uses |
| Storage | Postgres + S3 (or local FS for Phase 1) | boring, debuggable |
| Deployment | Single Docker container on Shipsy infra | not worth k8s for this |
| Telemetry | OpenTelemetry → existing Shipsy stack | for "which prompt cost what" |

## 7. Cost model (rough)

Per deck:
- Profile extraction: ~2k input + 1k output tokens
- Process flow design: ~6k input + 3k output (icons manifest in context)
- As-Is/To-Be/Impact: ~5k input + 3k output
- AgentFleet curation: ~3k input + 1k output
- Validate + repair: ~2k overhead

≈ 18k input + 8k output per deck. At Sonnet 4 pricing, **~$0.18 / deck**. 

100 decks/month for the team = **~$18/mo**. Negligible vs the SE-hour saved (~30-45 min per deck today).

## 8. Open questions for you to decide

1. **Repo location**: new repo in Shipsy GitHub? Monorepo with another tool? Public-but-private?
2. **API key ownership**: who pays + manages the Anthropic key? (suggest: shared Shipsy account, billed to pre-sales cost-centre)
3. **Deployment target**: Shipsy internal infra? Vercel? Render.com? AWS?
4. **First 5 users**: who's the closed-beta cohort? Their feedback shapes Phase 2.
5. **Style ownership**: who owns Shipsy's deck visual style going forward? If marketing changes the deck template, who updates render.py + reference decks?
6. **Iteration UX**: do SEs want to edit JSON directly (power-user) or only edit through the UI (PM-friendly)? Affects Phase 2 scope significantly.

## 9. What I'd do this week

If I were you, in order:

1. **Day 1** — finish Phase 0 (SKILL.md, QUICKSTART.md, push to repo). 2-3 power users on CC can use it tomorrow.
2. **Day 2-3** — extract the in-my-head discipline into `kb/` markdown files. This is a content task more than code. Pair with one SE who's done a Skynet deck before.
3. **Day 4-5** — scaffold the CLI (Phase 1). Get one transcript end-to-end working with the multi-stage agent.
4. **Week 2** — closed beta with 3 SEs on the CLI. Capture every gripe.
5. **Week 3+** — start Phase 2 UI based on what week-2 taught you.

Don't skip step 2. The KB is the moat — the renderer and orchestrator are commodity once the discipline is written down.

## 10. Things to NOT do

- Don't build a fine-tuned model. Sonnet + good prompts + good KB beats it for this kind of structured output, and you can iterate in hours instead of weeks.
- Don't use LangChain / LlamaIndex / etc. for this. ~500 LOC of plain Python beats a framework you have to debug into.
- Don't try to make the agent "fully autonomous" early. SEs want a draft they can edit, not a black box. Always show the JSON.
- Don't ship without a "regenerate this section" button. The all-or-nothing UX kills iteration.
- Don't store transcripts forever without a retention policy. Some client meetings are confidential — set a 90-day auto-delete and put it in the privacy notice.
