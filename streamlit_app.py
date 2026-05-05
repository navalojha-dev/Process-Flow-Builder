"""Streamlit Community Cloud deployment.

Alternative to the Vercel deploy. Streamlit Cloud has no per-request
timeout (unlike Vercel Hobby's 10-60s window), so the 30-45s pipeline
runs comfortably. Free tier, deploy in 5 min from GitHub.

To run locally:
    pip install -e .
    pip install streamlit
    streamlit run streamlit_app.py

To deploy:
    1. Push this repo to GitHub
    2. Go to https://share.streamlit.io
    3. Sign in with GitHub, click "New app"
    4. Pick the repo, branch=main, file=streamlit_app.py
    5. Advanced settings → Secrets:
           GEMINI_API_KEY = "..."
           PF_PROVIDER    = "gemini"
    6. Deploy. URL: https://<your-app>.streamlit.app
"""
from __future__ import annotations

import datetime as dt
import os
import tempfile
from pathlib import Path

import streamlit as st

# Pull secrets from Streamlit's secrets manager into env vars so the
# pf_builder package picks them up without code changes.
for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "PF_PROVIDER", "PF_GEMINI_MODEL"):
    if key in st.secrets:
        os.environ[key] = st.secrets[key]
os.environ.setdefault("PF_PROVIDER", "gemini")

from pf_builder.orchestrator import run_pipeline  # noqa: E402


VERTICALS = [
    "(auto-detect)",
    "fmcg-distribution",
    "container-drayage",
    "post-and-parcel",
    "pallet-network",
    "q-commerce",
    "3pl-cross-border",
    "cold-chain",
    "other",
]

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Shipsy Process Flow Builder",
    page_icon="📊",
    layout="centered",
)

st.markdown(
    "<h1 style='margin-bottom:0;'>📊 Shipsy Process Flow Builder</h1>"
    "<p style='color:#6B7280;margin-top:4px;'>"
    "Paste a client meeting transcript → get a 3-slide PPTX deck."
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ---------------------------------------------------------------------------
# Config check — fail fast with a clear message
# ---------------------------------------------------------------------------

if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "No LLM provider key configured. The deployer must set "
        "`GEMINI_API_KEY` (or `ANTHROPIC_API_KEY`) in Streamlit secrets."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------

mode_label = st.radio(
    "What do you want?",
    options=[
        "Whole deck (3 slides) — Process Flow + As-Is/To-Be/Impact + AgentFleet",
        "Process Flow only (1 slide) — faster, ~50% cheaper",
    ],
    index=0,
    help="The whole deck takes ~30-45s and uses 4 LLM calls. Process flow only takes ~10-15s and uses 2.",
)
mode = "flow_only" if mode_label.startswith("Process Flow only") else "full"

col1, col2 = st.columns([2, 1])
with col1:
    client_name = st.text_input(
        "Client name",
        placeholder="e.g. DP World Logistics",
        help="Used verbatim as the deck title.",
    )
with col2:
    vertical_choice = st.selectbox(
        "Vertical (optional)",
        VERTICALS,
        index=0,
        help="Speeds the agent up if you know it.",
    )

transcript = st.text_area(
    "Meeting transcript",
    height=240,
    placeholder=(
        "Paste raw meeting notes — bullets, half-sentences, multiple meetings "
        "concatenated all fine. The agent's first stage cleans it up."
    ),
    help=(
        "Specifics matter more than polish — tool names, scale numbers, "
        "time-window constraints, explicit AI asks."
    ),
)

build = st.button("Build deck", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

if build:
    if not client_name.strip():
        st.error("Client name is required.")
        st.stop()
    if not transcript.strip():
        st.error("Transcript is required.")
        st.stop()

    vertical = None if vertical_choice == "(auto-detect)" else vertical_choice

    progress = st.progress(0, text="Starting…")
    log_lines: list[str] = []
    log_box = st.empty()

    if mode == "full":
        stages = [
            ("Stage 1/5 · Extracting client profile…", 0.10),
            ("Stage 2/5 · Designing process flow…", 0.30),
            ("Stage 3/5 · Writing As-Is / To-Be / Impact matrix…", 0.55),
            ("Stage 4/5 · Curating AgentFleet…", 0.80),
            ("Stage 5/5 · Validating + repairing…", 0.92),
            ("Rendering deck…", 0.98),
        ]
    else:
        stages = [
            ("Stage 1/3 · Extracting client profile…", 0.20),
            ("Stage 2/3 · Designing process flow…", 0.65),
            ("Stage 3/3 · Validating + repairing…", 0.90),
            ("Rendering deck…", 0.98),
        ]

    def _on_progress(msg: str) -> None:
        log_lines.append(msg)
        # Match progress fraction to the stage prefix
        frac = next((f for prefix, f in stages if prefix.split(" · ")[0] in msg), None)
        if frac is None:
            frac = min(0.99, len(log_lines) * 0.15)
        progress.progress(frac, text=msg)
        log_box.code("\n".join(log_lines), language="text")

    try:
        with tempfile.TemporaryDirectory() as td:
            runs_root = Path(td) / "runs"
            run_dir = run_pipeline(
                transcript=transcript,
                client_name=client_name.strip(),
                vertical_hint=vertical,
                user="streamlit-web",
                runs_root=runs_root,
                progress=_on_progress,
                mode=mode,
            )
            pptx_path = next(run_dir.glob("*.pptx"), None)
            flow_path = run_dir / "flow.json"
            issues_path = run_dir / "issues.md"
            if pptx_path is None:
                st.error("Renderer returned no PPTX.")
                st.stop()

            pptx_bytes = pptx_path.read_bytes()
            flow_text = flow_path.read_text() if flow_path.exists() else "{}"
            issues_text = issues_path.read_text() if issues_path.exists() else ""

        progress.progress(1.0, text="✓ Done")

        date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        slug = "".join(c if c.isalnum() else "-" for c in client_name).strip("-")[:40]
        filename = f"{slug or 'client'}_process_flow_{date}.pptx"

        st.success(f"Built **{filename}** — click below to download.")
        st.download_button(
            "⬇️ Download PPTX",
            data=pptx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
        )

        with st.expander("Issues & assumptions (review before sharing the deck)"):
            st.markdown(issues_text or "_No issues recorded._")

        with st.expander("Raw flow.json (for power-user editing + re-render)"):
            st.download_button(
                "Download flow.json",
                data=flow_text,
                file_name=f"{slug}_flow.json",
                mime="application/json",
            )
            st.code(flow_text, language="json")

    except Exception as e:  # noqa: BLE001
        progress.empty()
        st.error(f"Build failed: {type(e).__name__}: {e}")
        st.exception(e)

st.divider()
st.caption(
    "Provider: "
    + os.environ.get("PF_PROVIDER", "gemini")
    + " · Model: "
    + os.environ.get("PF_GEMINI_MODEL", "gemini-2.5-flash")
    + " · Build time: ~30-45s · "
    + "Source: github.com/<your-org>/process-flow-builder"
)
