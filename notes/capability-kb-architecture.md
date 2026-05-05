# Capability KB Architecture — How the Agent Learns Shipsy

_Owner: Naval / Sharvani · Last updated: 2026-05-05_

The agent maps **client pain (from transcript)** → **Shipsy capability (cited in to-be bullets)**. To do that responsibly, it needs an authoritative, fresh, traceable picture of what Shipsy actually sells. This document spells out where that picture comes from.

## The honest current state (v0.1)

Today the agent reads ONE source: `pf_builder/kb/catalog.py`. That file is **my hand-curated synthesis** — 8 capability descriptions and 7 agent profiles, distilled from the existing Skynet / TPN / DPWorld reference decks. It's good enough for prototyping. It is not good enough to ship to teammates who'll quote it to real clients.

Three problems:

1. **Coverage** — 8 capabilities probably misses real Shipsy modules
2. **Accuracy** — my paragraph descriptions are deck-shaped, not engineering-shaped (no edge cases, integration constraints, customisation tiers)
3. **Freshness** — there's no update mechanism; every product change requires me to re-curate

The fix is to compose **5 sources** behind a single KB adapter. The agent always queries through the adapter; the adapter knows which source to call.

## The 5 sources, ranked by authority

| # | Source | What it gives | Authority | Freshness | Effort to wire |
|---|---|---|---|---|---|
| 1 | **DevRev articles** | Canonical product descriptions, AgentFleet catalog, integration docs | High (if product team owns) | Live | Medium (API + auth + cache) |
| 2 | **Shipsy codebase** | Ground-truth feature existence — proves a capability claim is real | Highest (running code) | Live | High (one-time mapping work) |
| 3 | **`slide-search` skill** | Customer-language framing, real proof points, vertical case studies | Medium (sales-shaped) | Stale-ish | Trivial — already available in CC |
| 4 | **Reference deck JSONs** | Few-shot examples of how capabilities show up in flows | Medium | Frozen | Already wired (`samples/*.json`) |
| 5 | **`catalog.py` fallback** | Last-resort inline bootstrap for when 1-4 fail or aren't wired yet | Low | Manual | Already wired |

**Composition principle**: agent prefers the highest-authority source that has signal. Lower sources fill gaps, not override.

## Per-source detail

### Source 1 — DevRev (the primary)

**What goes in DevRev**:
- One article per Shipsy capability (routing-engine, dispatch-control-tower, driver-app-epod, settlement-finance, customer-comms, analytics-bi, master-data, documentation, plus whatever I missed)
- One article per AgentFleet agent (ATLAS, ASTRA, NEXA, VERA, Address Intelligence, Routing Engine, Service Time AI, plus future ones)
- One article per vertical playbook (FMCG distribution, container drayage, post-and-parcel, pallet network, q-commerce, 3pl-cross-border, cold chain)
- One article per integration (Oracle EBS, SAP, Salesforce, ISIL, MoT KSA waybill portal)

**How the agent reads it**:

```python
# pf_builder/kb/devrev.py
class DevRevKB:
    def __init__(self, api_key, cache_dir="~/.pf/kb-cache"):
        self.client = DevRevClient(api_key)
        self.disk_cache = DiskCache(cache_dir, ttl_hours=6)
        self.lru = LRU(max_size=128)

    def search_capabilities(self, query: str, top_k: int = 5) -> list[Article]:
        cache_key = f"cap:{hash(query)}"
        if (cached := self.lru.get(cache_key)) is not None: return cached
        if (cached := self.disk_cache.get(cache_key)) is not None:
            self.lru[cache_key] = cached
            return cached
        results = self.client.articles.search(
            query=query, category="capabilities", top_k=top_k
        )
        self.disk_cache.set(cache_key, results)
        self.lru[cache_key] = results
        return results

    def get_agentfleet(self) -> list[Agent]:  # pre-fetched, small
        return self._cached_get("agentfleet/catalog")

    def get_vertical_playbook(self, vertical: str) -> Playbook:
        return self._cached_get(f"verticals/{vertical}")
```

**Where stages call it**:
- **Stage 3** (process_mapping): `search_capabilities(query)` — agent queries per pain point. Open-ended.
- **Stage 4** (ai_use_cases): `get_agentfleet()` — full catalog pre-fetched.
- **Stage 2** (process_flow): `get_vertical_playbook(vertical)` — pre-fetched per inferred vertical.

**Cache strategy** — two layers:
- **In-memory LRU** per orchestrator process (one render = many calls, no duplicate fetches)
- **Disk cache** with 6h TTL (most decks built within a 6h window of an SE's research session)

**Auth**: service account token (not a personal PAT) with read-only scope on the capabilities/agentfleet/verticals categories. Stored in `.env`, never committed.

### Source 2 — Shipsy codebase (the ground-truth check)

The codebase isn't read at runtime — it's used **once, offline, by Naval/Sharvani**, to build a static manifest of "what features actually exist". That manifest then validates DevRev's claims.

**Process** (one-time, repeated quarterly):

```bash
# Generate a feature manifest from the codebase
cd <shipsy-codebase>
pf-kb scan-codebase \
    --output /Users/shipsy/Process\ Flow\ Builder/.kb-cache/codebase-features.json
```

The scanner looks for:
- Module names in directory structure (`/services/routing/`, `/services/settlement/`)
- Public API endpoints (OpenAPI spec / Swagger / route definitions)
- Feature flags (`if FeatureFlag.ATLAS_AGENT_ENABLED:`)
- Module READMEs (docstrings → short capability summary)

Output: a JSON file mapping `capability-id → { code-paths, api-endpoints, feature-flags, status }`.

**How the agent uses it** — Stage 5 (validate). When Stage 3 cites `[atlas-agent]` in a to-be bullet, validator checks:
1. Does this capability exist in DevRev?
2. Does the codebase manifest have at least one matching `code-path` or `api-endpoint`?

If DevRev says yes but codebase says no → flag in `issues.md`: "Capability `atlas-agent` claimed in to-be but not found in codebase manifest. Verify with engineering before sharing the deck."

This is the safety net against marketing-shaped claims that don't have real product backing.

### Source 3 — `slide-search` skill (sales context)

The CC skill `anthropic-skills:slide-search` is described as: _"Shipsy's sales deck intelligence tool. Trigger on anything related to sales decks, presentations, slides, case studies."_ It's available **right now** with no setup.

**Use case**: when an SE drops a transcript with a niche pain that the DevRev catalog doesn't directly address, the agent calls `slide-search` to find historical decks where Shipsy solved a similar problem. The deck-level proof point becomes input to Stage 3.

Example query during Stage 3:
> "search Shipsy decks for how we solved cross-border KYC document compliance"
> → returns 3 decks where Shipsy did this for prior clients
> → agent extracts the capability framing and grounds the to-be bullet

**Why this is valuable even with DevRev wired up**: customers respond to **"we did this for company X"** more than to abstract capability descriptions. Slide-search surfaces those proof points; DevRev gives the technical accuracy.

**Wiring**: trivial. The CC skill is already available — when the orchestrator runs inside CC, Stage 3 can invoke it directly. When the orchestrator runs as a standalone CLI/web service, we'd need to expose slide-search via API or pre-fetch a snapshot.

### Source 4 — Reference deck JSONs (few-shot examples)

We already have these:
- `.claude/skills/process-flow/samples/tpn_flow.json`
- `/tmp/pf_runs/dpworld_flow.json`
- `/tmp/pf_runs/aljomaih_b2b_flow.json`
- `/Users/shipsy/Downloads/Anderson_*.pptx` (extractable)

**How they're used today**: in the Claude.ai Project setup, these are uploaded as project knowledge. The agent reads them as few-shot examples when designing slide 1 and writing matrix bullets.

**How to make this systematic**: extract a `samples/<vertical>.json` for every vertical you ship to. The agent's Stage 2 prompt loads the matching vertical's sample as inline context. This bridges the gap between abstract capability description (DevRev) and concrete deck shape.

**Maintenance**: every time an SE produces a deck the team is proud of, add it to `samples/`. Annual review to retire stale ones.

### Source 5 — `catalog.py` fallback

The 8 capabilities + 7 agents I curated. **Stays in the codebase as the bootstrap fallback** for:
- New deployments before DevRev integration is set up
- Air-gapped runs (offline, no DevRev API access)
- DevRev outages

The KB adapter checks DevRev first, falls back to `catalog.py` if DevRev returns no results or 5xx errors. SEs see a warning in `issues.md`: _"Built using fallback catalog — DevRev was unreachable. Verify capability claims manually before sharing."_

## Composition — how Stage 3 actually calls them

Concrete walkthrough for a single transcript line: _"12 planners + dispatchers spending 3-4 hrs/day in Roadnet"_

```
Stage 3 prompt receives:
  - transcript line
  - profile (vertical=fmcg-distribution)

Stage 3 LLM calls (via tools):

  1. devrev.search_capabilities("legacy routing tool replacement")
     → [routing-engine article, dispatch-control-tower article]

  2. devrev.get_vertical_playbook("fmcg-distribution")  [pre-fetched]
     → playbook.common_pain mentions "planner effort in legacy routing tool"

  3. (optional) slide_search("FMCG day delivery routing engine replacement")
     → returns 2 historical decks (Aljomaih, Coca-Cola Saudi)
     → agent extracts proof framing

LLM assembles to-be bullet:

  "[routing-engine] handles 200+ constraints natively (Ramadan, school,
   cameras), eliminating the Roadnet remote-desktop dependency"

Stage 5 (validate) checks:
  ✓ "routing-engine" is in DevRev capabilities catalog
  ✓ codebase-features.json has at least one entry for "routing-engine"
  → bullet passes

If codebase-features.json is missing the routing-engine entry:
  ⚠ issues.md notes: "Capability 'routing-engine' cited in to-be was
    not found in the codebase manifest (last scan: 2026-04-30). Verify
    with engineering."
```

That's the full chain — pain → search → ground → cite → validate.

## Maintenance loop (the part that actually matters long-term)

The KB rots if no one waters it. Three loops:

### Loop 1 — DevRev as source of truth (continuous)

- DevRev articles are owned by **Shipsy product team** (whoever owns product marketing today)
- Naval/Sharvani are **consumers**, not editors — if a capability description is wrong, file a DevRev ticket, don't edit it locally
- Quarterly review: product team scans the article list, retires stale ones, adds new ones

### Loop 2 — Codebase scan (quarterly)

- `pf-kb scan-codebase` runs every quarter (or on a CI schedule)
- Output is committed to `.kb-cache/codebase-features.json`
- Diff against last scan flags new/removed capabilities → product team confirms intent → DevRev articles updated to match

### Loop 3 — SE feedback (continuous)

- Every deck has `issues.md` with the capability citations called out
- SEs flag bad citations → opens a ticket
- Top 5 tickets per month feed back into:
  - DevRev article fixes (if description was wrong)
  - `catalog.py` fixes (if fallback was wrong)
  - Vertical playbook tweaks (if pain mapping was off)

## Phase plan — what we wire and when

### Week 1 — DevRev integration (highest ROI)

1. Get a service account token from whoever owns DevRev access at Shipsy
2. Build `pf_builder/kb/devrev.py` with the adapter shown above
3. Migrate the 8 capabilities + 7 agents from `catalog.py` into DevRev articles (one-time content move)
4. Switch the agent to query DevRev primary, `catalog.py` fallback
5. Smoke test: one Aljomaih run, one DPWorld run, compare to current output

### Week 2-3 — Codebase scan (the validation layer)

1. Build `pf-kb scan-codebase` — scans the Shipsy codebase Naval has locally
2. Generate first `codebase-features.json` snapshot
3. Wire it into Stage 5 validate as a soft check (warn, don't fail)
4. Have one Shipsy engineer review the snapshot — confirm it matches their mental model

### Week 4 — Slide search wiring

1. If running in CC: invoke `slide-search` skill from Stage 3 via tool call
2. If running standalone: pre-fetch a snapshot of relevant decks per vertical, store in `kb/sales-snapshots/`
3. Add as Stage 3 context tool

### Month 2+ — Iterate based on real usage

- Track which capability claims SEs flag as wrong (Loop 3 feedback)
- Decide what additional sources to wire (engineer interviews? OpenAPI spec? CRM case studies?)
- Build vertical playbook articles for whatever vertical comes up most in real usage

## Honest tradeoffs

**Why not just rely on the LLM's training knowledge?**
The model knows logistics generically. It does NOT know Shipsy specifically. Without a grounded KB, the agent will invent capabilities that *sound* like Shipsy products but aren't. That's the worst-case failure mode — a deck that confidently claims a feature Shipsy doesn't ship.

**Why not just one source (DevRev)?**
DevRev is editorial — product team writes for marketing. The codebase scan catches the gap between "what we say" and "what we ship". Slide-search adds proof points DevRev articles often lack. Each source compensates for the others' weakness.

**Why not pre-fetch everything?**
Stage 3 queries are open-ended (driven by transcript pain phrases). You can't pre-fetch what you don't know to ask. Tool calls let the LLM search per-pain. The cost is a few extra LLM tokens per stage.

**Why not skip catalog.py entirely once DevRev is up?**
Two reasons: (1) bootstrap when DevRev isn't yet provisioned for a new environment, (2) graceful degradation when DevRev is down. The fallback is cheap to maintain and meaningful insurance.

## Open questions for you to decide

1. **Who at Shipsy owns DevRev capability articles?** — needs a named human, not a team
2. **Service account vs personal PAT for DevRev?** — strongly prefer service account
3. **Is the codebase you have local the full Shipsy codebase, or one repo?** — affects scope of the codebase scan
4. **`slide-search` skill — is it available outside CC?** — affects whether we can use it from a standalone CLI/web deployment
5. **Quarterly cadence for codebase scan, or every release?** — depends on Shipsy's release rhythm

The agent's quality is bottlenecked on the KB more than on the LLM. Investing in this is the highest-leverage thing we can do for the Process Flow Builder.
