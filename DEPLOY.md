# Deploy

Two free-tier paths. **Streamlit Cloud is recommended** — no per-request
timeout, deploys cleanly from GitHub, fits the 30-45s pipeline. Vercel
Hobby may or may not fit depending on Vercel's current `maxDuration`
limit (it's been moving), so I'd treat Vercel as Plan B.

| | **Streamlit Cloud** (recommended) | Vercel Hobby |
|---|---|---|
| Per-request timeout | None | 10-60s (varies) |
| Cold start | 30-60s after sleep | <1s warm |
| Free quota | 1 app, generous | 100GB-h/month |
| Frontend | Streamlit (Python widgets) | Static HTML |
| Deploy effort | 5 min | 5 min |
| Best for | All use cases on free tier | If you also want Pro later |

Both paths require the same step 1 (push to GitHub).

## Architecture (what gets deployed)

```
Browser → public/index.html (static)
       → POST /api/build {client, vertical, transcript}
              ↓
         api/build.py (Vercel Python serverless function)
              ↓
         pf_builder.orchestrator (5-stage agent + renderer)
              ↓
         PPTX bytes streamed back as a file download
```

No persistent storage. No previews. Single PPTX per request.

---

## Step 1 — Push to GitHub (3 minutes)

### 1a. Create the GitHub repo

In the browser:

1. Go to **https://github.com/new**
2. Repository name: `process-flow-builder`
3. Owner: your Shipsy org (or your personal account if you don't have admin on the org yet)
4. **Set visibility to Private** (this contains internal sales tooling)
5. Do **not** initialise with README, .gitignore, or license — we already have those locally
6. Click **Create repository**

### 1b. Push the local repo

Run in your terminal:

```bash
cd "/Users/shipsy/Process Flow Builder"
git init
git add -A
git commit -m "Initial: Process Flow Builder v0.1 — CLI + Vercel web app"
git branch -M main
git remote add origin git@github.com:<your-org>/process-flow-builder.git
git push -u origin main
```

If you don't have SSH set up with GitHub, use the HTTPS URL instead (`git remote add origin https://github.com/<your-org>/process-flow-builder.git`) — git will prompt for a personal access token.

**Verify** `.env` is NOT in the push:

```bash
git ls-files | grep -i env       # should print: .env.example  (not .env)
```

If `.env` shows up, run `git rm --cached .env && git commit -m "ignore .env" && git push`. Never let credentials reach the repo.

---

## Step 2A — Deploy on Streamlit Cloud (recommended, 5 minutes)

### 2A.1 Sign in

1. Go to **https://share.streamlit.io**
2. Click **Sign in** → **Continue with GitHub**
3. Authorise the Streamlit app to read your GitHub repos

### 2A.2 New app

1. Click **New app**
2. **Repository**: pick `<your-org>/process-flow-builder`
3. **Branch**: `main`
4. **Main file path**: `streamlit_app.py`
5. **App URL**: pick a sub-domain like `shipsy-process-flow.streamlit.app`
6. Click **Advanced settings** → **Secrets** and paste:

   ```toml
   GEMINI_API_KEY = "<your key from https://aistudio.google.com/apikey>"
   PF_PROVIDER = "gemini"
   PF_GEMINI_MODEL = "gemini-2.5-flash"
   ```

7. Click **Deploy**

First deploy takes ~3 minutes (Streamlit installs `requirements.txt` deps).

### 2A.3 Test the URL

When the build finishes you get `https://<your-subdomain>.streamlit.app`. Open it and run a build through the Aljomaih transcript. The form has the same 3 inputs + a download button when complete.

### 2A.4 Plan limits to know about

- **Sleep on inactivity**: app sleeps after ~12h with no traffic; first request after sleep takes ~30-60s extra to wake the container. Repeat hits stay warm.
- **Resource cap**: 1 GB RAM, 1 GB disk. Plenty for our pipeline.
- **No request timeout**: pipeline can take 60s+ without issue.
- **Public by default**: anyone with the URL can use it. To restrict to teammates, see "App authentication" in Streamlit Cloud settings (free tier supports OAuth via GitHub / SSO).

---

## Step 2B — Deploy on Vercel (5 minutes)

### 2a. Import the repo

1. Go to **https://vercel.com/new**
2. Sign in with GitHub (the same account you pushed to)
3. Click **Import** next to the `process-flow-builder` repo
4. Project name: leave default
5. Framework preset: **Other** (Vercel will auto-detect the Python function from `vercel.json`)
6. Root directory: leave as `./`
7. Build / output / install: leave defaults — `vercel.json` overrides what's needed

**Don't click Deploy yet.** First add environment variables.

### 2b. Set environment variables

Before deploying, expand **Environment Variables** on the import page and add:

| Name | Value | Environment |
|---|---|---|
| `GEMINI_API_KEY` | _(your Gemini key from https://aistudio.google.com/apikey)_ | Production + Preview + Development |
| `PF_PROVIDER` | `gemini` | Production + Preview + Development |
| `PF_GEMINI_MODEL` | `gemini-2.5-flash` _(optional — already the default)_ | Production + Preview + Development |

Then click **Deploy**.

First deploy takes ~2 minutes (Vercel pulls Python deps and bundles the function).

### 2c. Test the live URL

Vercel gives you a URL like `https://process-flow-builder-<hash>.vercel.app`. Open it and:

1. Paste a transcript into the textarea
2. Type a client name
3. (Optional) pick a vertical
4. Click **Build deck**
5. Wait ~30-45 seconds
6. The PPTX downloads automatically

If it errors, check **Vercel project → Logs → Functions** to see the Python traceback.

### 2d. (Optional) Add a custom domain

In Vercel project → **Settings → Domains**, add something like `pf.shipsy.io` (you'll need DNS access to point a CNAME at Vercel). Not required for beta.

---

## Step 3 — Hand it to teammates

Send a Slack DM to the 2-3 SE beta users:

```
Built a tool that turns a client meeting transcript into a Skynet-styled
3-slide PPTX in ~30s. URL: <your-vercel-url>

Inputs you provide:
  • Client name (required)
  • Vertical hint (optional but recommended)
  • Meeting transcript (required — paste raw notes, messy fine)

Output: PPTX file downloads automatically.

Bring me a bug list after your first 3 decks.
```

---

## Plan limits — important caveats

### Vercel function timeout

- **Hobby plan**: 10s max — too short for our pipeline (which takes 30-45s). Build will time out and the user sees an error.
- **Pro plan ($20/month)**: 60s max — works.
- **Enterprise**: 900s — overkill.

`vercel.json` requests `maxDuration: 60`, which is honored on Pro+. If you stay on Hobby, the build will likely time out.

### Vercel function size

The Python bundle compressed should be ~15-20MB — well under the 50MB limit. If a future change adds a heavy dep (anthropic SDK, google-genai SDK, etc.), the deploy may break. Keep deps lean.

### Gemini free-tier rate limits

- Daily token limit per project (changes over time — currently generous on Flash)
- Per-minute requests: 15 RPM on free tier
- For >5 SEs hitting it concurrently, switch to a paid tier or an Anthropic key

---

## Inputs the user provides → what comes back

**Inputs (form on the live URL)**:
- `client` (text, required) — e.g. "DP World Logistics"
- `vertical` (dropdown, optional) — one of the 7 + "auto-detect"
- `transcript` (textarea, required) — raw meeting notes

**Output**:
- A `.pptx` file downloads to the user's machine
- Filename: `<Client>_process_flow_<YYYY-MM-DD>.pptx`
- Contents: 3 slides (Process Flow, As-Is/To-Be/Impact, AgentFleet)

**No** previews, no `issues.md`, no `flow.json`, no run history — those exist only in the local CLI (`pf build`). The web app is intentionally minimal.

---

## Updating the deployed app

```bash
# Make changes locally
git add -A
git commit -m "fix: <what changed>"
git push
# Vercel auto-deploys from GitHub on every push to main (~1 min)
```

Pull requests get their own Preview deployments automatically.

---

## Rollback

If a deploy breaks production:

1. Go to **Vercel project → Deployments**
2. Find the last green deployment
3. Click ⋯ → **Promote to Production**

Takes ~10 seconds. Don't bother reverting git first; do that after you've stopped the bleeding.
