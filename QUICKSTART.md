# Process Flow Builder — Quickstart

Turn a client-meeting transcript into a Skynet-styled 3-slide PPTX deck in ~30 seconds.

## What you get

```
runs/<run_id>/
├── deck.pptx           ← the deliverable
├── flow.json           ← agent's curated structure (you can edit)
├── previews/*.png      ← review without opening PowerPoint
├── issues.md           ← what the agent guessed / wants confirmed
└── run_metadata.json   ← model, tokens, time, cost
```

## One-time setup (5 min)

```bash
# 1. Clone
git clone <shipsy-repo-url> "Process Flow Builder"
cd "Process Flow Builder"

# 2. Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Pick ONE LLM provider and set its key
#    (a) Anthropic Claude — recommended for quality
export ANTHROPIC_API_KEY="sk-ant-..."          # ask Sharvani / Naval

#    (b) OR Google Gemini — cheaper, get a key at https://aistudio.google.com/apikey
export GEMINI_API_KEY="..."

# 4. (Optional, for previews) — install LibreOffice + Poppler
brew install --cask libreoffice
brew install poppler
```

Verify:
```bash
pf --help
```

## Usage

### Full pipeline — transcript → deck

```bash
pf build meeting-notes.txt --client "DP World Logistics"
```

With a vertical hint (saves a guess, slightly better quality):
```bash
pf build meeting-notes.txt \
    --client "DP World Logistics" \
    --vertical container-drayage
```

Vertical options: `fmcg-distribution`, `container-drayage`, `post-and-parcel`,
`pallet-network`, `q-commerce`, `3pl-cross-border`, `cold-chain`, `other`.

Pick provider (defaults to Anthropic):
```bash
pf build meeting-notes.txt --client "DP World" --provider gemini
```

Or set once for the shell:
```bash
export PF_PROVIDER=gemini
pf build meeting-notes.txt --client "DP World"
```

Override the model used per-provider (defaults shown):
```bash
export PF_ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
export PF_GEMINI_MODEL=gemini-2.5-pro     # or gemini-2.5-flash for cheaper runs
```

### Render a hand-edited JSON

If you tweaked `flow.json` and just want a fresh PPTX:
```bash
pf render outputs/runs/<run_id>/flow.json
```

### Validate a JSON before rendering

```bash
pf validate outputs/runs/<run_id>/flow.json
```

Catches: unknown icon names, agents not in catalog, labels >60 chars, schema violations.

### Dry-run (no API calls)

Useful to verify your install before spending tokens:
```bash
pf dry-run /path/to/some/flow.json
```

## What the transcript should look like

Messy is fine. Bullets, half-sentences, multiple meetings concatenated — the
agent's first stage cleans it up. Don't pre-format. Examples that work:

```
Met DPW today. They run container drayage out of Jebel Ali, also
Sohar. Cross-border to Oman & KSA. Mostly internal BUs but some
external. Pain: bookings on email/phone. No telematics. Drivers
get jobs over WhatsApp. CRO tokens / EIRs are paper. Cross-border
permits — only the dispatcher knows who has what visa.
```

## Iteration

The deck is a **draft**, not a black box. Open `issues.md` first — it lists
what the agent guessed and what to verify. Then either:

- **Tweak `flow.json` directly** and run `pf render flow.json` to re-render.
- **(Coming soon)** `pf rebuild <run_id> --section process_mapping` —
  regenerate one slide against an updated transcript.

## Cost & time

- ~$0.18 per deck at current Sonnet pricing
- ~30-45s wall time per `pf build`
- Shared Anthropic key, billed to pre-sales cost-centre

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ANTHROPIC_API_KEY is not set` | `export ANTHROPIC_API_KEY=...` (ask team for shared key) |
| `pf: command not found` | `source .venv/bin/activate` |
| Previews missing | Install LibreOffice + Poppler (see setup step 4) |
| Deck looks wrong / agent missed a pain point | Add detail to transcript, re-run, OR edit `flow.json` and `pf render` |
| Schema validation fails after a hand-edit | `pf validate flow.json` — fix the listed issues |

## Files of interest

- `notes/agent-contract.md` — full input/output contract spec
- `notes/architecture-and-plan.md` — phased roll-out and design rationale
- `.claude/skills/process-flow/schema.json` — JSON schema the renderer expects
- `.claude/skills/process-flow/icons/manifest.json` — icon library + aliases

## Asking for help

Ping Naval or Sharvani in `#pre-sales-tools` Slack. Include:
- The `run_id` (from the bundle directory name)
- `issues.md` contents
- What you expected vs what came out
