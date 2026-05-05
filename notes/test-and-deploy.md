# Test & Deploy Runbook

_Owner: Naval / Sharvani · Last updated: 2026-05-04_

Two phases: **A** = prove it works on your laptop today. **B** = hand it to 2-3 beta teammates this week.

---

## Phase A — Test locally (today, ~10 min)

### A.1 Get an API key

Pick one. Both work; Gemini is free up to a generous free tier, Anthropic is more reliable for Stage 2 quality.

**Gemini (recommended for first test — free)**
1. Go to https://aistudio.google.com/apikey
2. Sign in with your Shipsy Google account
3. Click "Create API key"
4. Copy it

```bash
export GEMINI_API_KEY="paste-key-here"
```

**Anthropic (better quality, paid)**
1. Go to https://console.anthropic.com/settings/keys
2. Create a key (needs billing set up — ask Sharvani if you don't have it)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### A.2 Activate the venv

```bash
cd "/Users/shipsy/Process Flow Builder"
source .venv/bin/activate
pf --help        # should print usage
```

### A.3 First real run — Gemini

We already have an Aljomaih transcript saved from earlier work. Use it as the first test:

```bash
pf build /tmp/pf_runs/aljomaih_transcript.md \
    --client "Aljomaih · Pepsi KSA" \
    --vertical fmcg-distribution \
    --provider gemini
```

What you should see:
- `Provider: gemini` printed
- 5 progress lines (`Stage 1/5 · Extracting client profile…` etc.)
- A summary table with token counts per stage
- Green `✓ Bundle: outputs/runs/<run_id>/`
- The PPTX auto-opens (`--no-open` to disable)

Total time: ~30-60 seconds.

### A.4 Inspect the output

```bash
RUN_DIR=$(ls -td outputs/runs/*/ | head -1)
echo "Latest run: $RUN_DIR"

# 1. Look at the deck slides
open "$RUN_DIR/previews/slide-1.png"   # process flow
open "$RUN_DIR/previews/slide-2.png"   # as-is/to-be/impact
open "$RUN_DIR/previews/slide-3.png"   # AgentFleet

# 2. Read what the agent guessed
cat "$RUN_DIR/issues.md"

# 3. The actual deck
open "$RUN_DIR"/*.pptx
```

### A.5 What "good" looks like

You're judging **slide 1** primarily. Ask yourself:

- ✅ Does the row structure look like Aljomaih (FMCG day-delivery), not generic logistics?
- ✅ Are there 5-7 rows including warehouse + store-side adherence (specific to FMCG)?
- ✅ Do step labels mention concrete things from the transcript (Ramadan, MoT waybill, 5 AM/7 AM dispatch, supermarket receiving 06:30-12:30)?
- ❌ Red flag: generic rows like "Order → Pickup → Delivery → Done"
- ❌ Red flag: agent invented facts not in the transcript

If slide 1 is generic, the model isn't applying the keep/modify/remove/add discipline — that's the signal to retry with Anthropic, or improve the prompt.

### A.6 A/B test — same transcript, both providers

```bash
# Make sure both keys are set
export ANTHROPIC_API_KEY=...
export GEMINI_API_KEY=...

pf build /tmp/pf_runs/aljomaih_transcript.md \
    --client "Aljomaih · Pepsi KSA" \
    --vertical fmcg-distribution \
    --provider anthropic --no-open

pf build /tmp/pf_runs/aljomaih_transcript.md \
    --client "Aljomaih · Pepsi KSA" \
    --vertical fmcg-distribution \
    --provider gemini --no-open

# Compare the two latest bundles side by side
ls -td outputs/runs/*/ | head -2
```

Open both `slide-1.png` files in Preview side by side. The deck that's more
Aljomaih-specific (mentions Ramadan, MoT, 5 AM dispatch, etc.) is the winner.

If they're roughly equivalent, ship Gemini for cost. If Anthropic is meaningfully
better on slide 1, ship the **hybrid mode** — but that's a v0.2 follow-up.

### A.7 Edge cases to test next

Once the Aljomaih run looks right, try:

- **Different vertical** — paste a DPWorld-style transcript, see if the agent
  picks `container-drayage` correctly.
- **Vague transcript** — give it a 5-line summary, see how `issues.md` flags
  the gaps.
- **Wrong vertical hint** — set `--vertical post-and-parcel` for an FMCG
  transcript, see if Stage 1 overrides it.
- **Hand-edit the JSON** — open `flow.json`, tweak a step label, run
  `pf render flow.json` to re-render without LLM cost.

---

## Phase B — Beta to 2-3 teammates (this week, ~30 min)

Don't hand to the whole team. Pick 2-3 SEs / pre-sales who:
- Have actually built a Skynet-style deck before (so they can judge quality)
- Are tolerant of v0.1 rough edges
- Will write down what breaks

### B.1 Push to a git repo

The repo doesn't have a `.git/` yet. Create a private Shipsy GitHub repo first.

```bash
cd "/Users/shipsy/Process Flow Builder"

# Create a sensible .gitignore before first commit
cat > .gitignore <<'EOF'
.venv/
.DS_Store
*.pyc
__pycache__/
*.egg-info/
outputs/runs/        # SE-generated bundles, don't pollute the repo
.env
EOF

git init
git add -A
git commit -m "Initial: Process Flow Builder v0.1"

# After creating the repo on GitHub.com under Shipsy org:
git remote add origin git@github.com:<shipsy-org>/process-flow-builder.git
git branch -M main
git push -u origin main
```

### B.2 Decide on the API key model

Three options, pick one:

| Model | Pro | Con |
|---|---|---|
| **Each SE gets their own Gemini key** (free) | No shared billing, no secret management | Quotas per-key may bite at scale |
| **Shared Anthropic key** (paid) | Best quality, cleanest ops | Need to rotate if it leaks; bill goes to one cost-centre |
| **Shared Gemini key** (cheap) | Cheap + quality is decent | One bad SE → quota drained for everyone |

For 5 beta users I'd go **"each SE gets their own Gemini key"** — free, no ops.

For full team rollout, switch to a **shared Anthropic key** in a secret manager.

### B.3 Write a teammate-facing setup script

Save as `setup.sh` at the repo root (one-time, ~30 lines, see Phase 0 in
`notes/architecture-and-plan.md`). Pre-flight checks: Python ≥ 3.10, venv
creation, dep install, optional LibreOffice/Poppler for previews, prompts
for which provider key to set.

### B.4 The actual handoff

Send each beta user a Slack DM:

```
Hey — built a tool that turns a client meeting transcript into a Skynet-styled
3-slide deck in ~30s. Want to try it?

Repo: <url>
Setup (5 min): see QUICKSTART.md in the repo
Get a free Gemini key here: https://aistudio.google.com/apikey

Bring me a bug list after your first 3 decks.
```

### B.5 What to track for first 3 weeks

Keep a running google doc or Linear board for the beta:

- **Quality bugs** — "deck for X was generic on slide 1" → track which provider, save the run_id
- **Renderer bugs** — overflow / layout issues → screenshot + run_id
- **UX gripes** — "wished I could do X" → drives Phase 2 (web UI) backlog
- **Killer wins** — "saved me 40 min on the X deck" → ammo for wider rollout

After 3 weeks of beta, decide: roll wider, fix top 3 bugs first, or rethink something fundamental.

---

## Phase C — Production deploy (later)

Don't think about this now. After beta lands, the choices are:

1. **Stay CLI** — works for ~10 SEs, no infra needed.
2. **Web UI** (Phase 2 of the architecture plan) — needed past ~10 SEs.
3. **Slack bot** — needed if SEs live in Slack during deal cycles.

Decision driver: how many SEs are using it weekly. If <10, stay CLI. If 10-30,
build the web UI. If 30+, do both.

---

## Cheat sheet — every command in one place

```bash
# Setup (one-time)
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
export GEMINI_API_KEY=...    # or ANTHROPIC_API_KEY

# Build a deck
pf build transcript.txt --client "Aljomaih" --vertical fmcg-distribution
pf build transcript.txt --client "DP World" --provider gemini

# Re-render a hand-edited JSON (no LLM cost)
pf render outputs/runs/<run_id>/flow.json

# Validate a JSON before rendering
pf validate flow.json

# Smoke-test the renderer + bundle writer (no LLM)
pf dry-run /tmp/pf_runs/aljomaih_b2b_flow.json

# Switch provider per-shell
export PF_PROVIDER=gemini
export PF_GEMINI_MODEL=gemini-2.5-flash    # cheaper, worse Stage 2
export PF_GEMINI_MODEL=gemini-2.5-pro      # default
```
