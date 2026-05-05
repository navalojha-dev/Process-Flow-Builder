"""Multi-stage agent pipeline.

Runs the 5 stages in order, assembles the flow.json, and hands off to
the bundle writer. Each stage is timed and its token usage recorded.

Rate-limit pacing
-----------------
On free-tier LLM accounts (Gemini AI Studio, Anthropic free trial), the
per-minute request quota is small (~15 RPM on Gemini Flash). Bursting 4
stage requests in ~10s reliably trips a 429.

We pace stages by sleeping a fixed gap between requests. With a 5s gap:

    full mode: 4 requests over ~50s wall time = ~5 RPM (safe).
    flow_only: 2 requests over ~17s wall time = ~7 RPM (safe).

The gap is configurable via env var `PF_INTER_STAGE_DELAY_SECONDS`
(default 5). Set to 0 for paid tiers where bursting is fine.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable

from .bundle import RunRecord, StageStat, write_bundle
from .stages import ai_use_cases, process_flow, process_mapping, profile, validate

ProgressFn = Callable[[str], None]

# How long to wait between stage LLM calls so we don't burst over the
# free-tier per-minute quota. Tunable via env; default 5s.
DEFAULT_INTER_STAGE_DELAY = float(
    os.environ.get("PF_INTER_STAGE_DELAY_SECONDS", "5")
)


def _noop(_msg: str) -> None:
    pass


def _pace(progress: ProgressFn, seconds: float, stage_label: str) -> None:
    """Sleep with a visible progress message — 1s ticks so the UI stays alive."""
    if seconds <= 0:
        return
    remaining = float(seconds)
    while remaining > 0:
        progress(
            f"⏱  Pacing {remaining:.0f}s before {stage_label} "
            f"(staying under free-tier rate limit)…"
        )
        chunk = min(1.0, remaining)
        time.sleep(chunk)
        remaining -= chunk


def _split_assumptions(raw_text: str) -> list[str]:
    """Pull out 'assumptions:' / 'design notes:' / 'notes:' lines from the
    free-text trailing each stage's JSON block.
    """
    lines: list[str] = []
    # Drop the fenced block; everything after it is commentary.
    after_fence = re.split(r"```", raw_text)
    if len(after_fence) >= 3:
        tail = "".join(after_fence[2:])
    else:
        tail = ""
    for line in tail.splitlines():
        line = line.strip(" -•\t")
        if not line:
            continue
        # Skip headers like "Assumptions:" themselves.
        if re.match(r"^(assumptions?|design notes?|notes?)\s*:\s*$", line, re.I):
            continue
        lines.append(line)
    return lines


def run_pipeline(
    *,
    transcript: str,
    client_name: str,
    vertical_hint: str | None = None,
    user: str = "unknown",
    runs_root: Path = Path("outputs/runs"),
    progress: ProgressFn = _noop,
    mode: str = "full",
    inter_stage_delay_seconds: float | None = None,
) -> Path:
    """End-to-end run. Returns the run directory.

    `mode`:
      - "full"      — run all 5 stages, produce a 3-slide deck (default).
      - "flow_only" — run stages 1, 2, 5 only. Produce a 1-slide deck
                      (just the Process Flow). Skips the As-Is/To-Be/Impact
                      matrix and the AgentFleet card grid.
                      Faster (~10-15s saved) and cheaper (~50% fewer tokens).

    `inter_stage_delay_seconds`:
      - None (default) → use `PF_INTER_STAGE_DELAY_SECONDS` env var, then 5.
      - 0              → no pacing (bursts all stages — only safe on paid tiers).
      - >0             → sleep this many seconds between stage LLM calls.
    """
    if mode not in ("full", "flow_only"):
        raise ValueError(f"mode must be 'full' or 'flow_only', got {mode!r}")

    pace_seconds = (
        DEFAULT_INTER_STAGE_DELAY
        if inter_stage_delay_seconds is None
        else float(inter_stage_delay_seconds)
    )

    run = RunRecord(
        user=user,
        client_name=client_name,
        vertical="other",  # filled in after stage 1
        mode=mode,
        flow={},
    )

    # ---- Stage 1: Profile -------------------------------------------------
    progress("Stage 1/5 · Extracting client profile…")
    t0 = time.monotonic()
    s1 = profile.run(
        transcript=transcript,
        client_name=client_name,
        vertical_hint=vertical_hint,
    )
    run.stages.append(
        StageStat(
            name="profile",
            input_tokens=s1.input_tokens,
            output_tokens=s1.output_tokens,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
    )
    run.model = s1.model
    run.assumptions.extend(_split_assumptions(s1.raw_text))
    profile_data = s1.data
    run.vertical = profile_data.get("vertical", "other")

    _pace(progress, pace_seconds, "Stage 2 · Process Flow")

    # ---- Stage 2: Process Flow -------------------------------------------
    progress("Stage 2/5 · Designing process flow…")
    t0 = time.monotonic()
    s2 = process_flow.run(profile=profile_data, transcript=transcript)
    run.stages.append(
        StageStat(
            name="process_flow",
            input_tokens=s2.input_tokens,
            output_tokens=s2.output_tokens,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )
    )
    run.notes.extend(_split_assumptions(s2.raw_text))
    flow_block = s2.data

    if mode == "full":
        _pace(progress, pace_seconds, "Stage 3 · Process Mapping")

        # ---- Stage 3: Process Mapping ------------------------------------
        progress("Stage 3/5 · Writing As-Is / To-Be / Impact matrix…")
        t0 = time.monotonic()
        s3 = process_mapping.run(
            profile=profile_data,
            process_flow=flow_block,
            transcript=transcript,
        )
        run.stages.append(
            StageStat(
                name="process_mapping",
                input_tokens=s3.input_tokens,
                output_tokens=s3.output_tokens,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        )
        run.notes.extend(_split_assumptions(s3.raw_text))
        mapping_block = s3.data

        _pace(progress, pace_seconds, "Stage 4 · AgentFleet")

        # ---- Stage 4: AgentFleet -----------------------------------------
        progress("Stage 4/5 · Curating AgentFleet…")
        t0 = time.monotonic()
        s4 = ai_use_cases.run(
            profile=profile_data,
            process_flow=flow_block,
            process_mapping=mapping_block,
            transcript=transcript,
        )
        run.stages.append(
            StageStat(
                name="ai_use_cases",
                input_tokens=s4.input_tokens,
                output_tokens=s4.output_tokens,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        )
        run.notes.extend(_split_assumptions(s4.raw_text))
        agents_block = s4.data
    else:
        # flow_only: skip stages 3 & 4, leave matrix and agent-card sections empty.
        progress("Skipping Stage 3 (As-Is / To-Be / Impact) — flow_only mode")
        progress("Skipping Stage 4 (AgentFleet) — flow_only mode")
        mapping_block = []
        agents_block = []

    # ---- Assemble -------------------------------------------------------
    flow = {
        "client": profile_data,
        "process_flow": flow_block,
        "process_mapping": mapping_block,
        "ai_use_cases": agents_block,
    }

    # ---- Stage 5: Validate + Repair --------------------------------------
    label = "Stage 5/5" if mode == "full" else "Stage 3/3"
    progress(f"{label} · Validating + repairing…")
    t0 = time.monotonic()
    repaired, remaining_errors, repair_result = validate.validate_and_repair(
        flow, mode=mode,
    )
    if repair_result is not None:
        run.stages.append(
            StageStat(
                name="validate",
                input_tokens=repair_result.input_tokens,
                output_tokens=repair_result.output_tokens,
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        )
    else:
        run.stages.append(
            StageStat(
                name="validate",
                duration_ms=int((time.monotonic() - t0) * 1000),
            )
        )
    run.flow = repaired
    run.repair_errors = remaining_errors

    # ---- Render bundle ---------------------------------------------------
    progress("Rendering deck + previews…")
    return write_bundle(run, runs_root)
