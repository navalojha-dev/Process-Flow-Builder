"""Bundle writer — produces the run_id directory the contract spec promises.

    runs/<run_id>/
      ├── deck.pptx
      ├── flow.json
      ├── previews/{slide-1,2,3}.png
      ├── issues.md
      └── run_metadata.json

`runs/` lives under `outputs/runs/` by default so it sits next to the
existing one-shot decks teammates already use.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ulid

from . import render_adapter


@dataclass
class StageStat:
    name: str
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


@dataclass
class RunRecord:
    user: str
    client_name: str
    vertical: str
    mode: str
    flow: dict
    stages: list[StageStat] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    repair_errors: list[str] = field(default_factory=list)
    started_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    model: str = ""

    @property
    def total_tokens_in(self) -> int:
        return sum(s.input_tokens for s in self.stages)

    @property
    def total_tokens_out(self) -> int:
        return sum(s.output_tokens for s in self.stages)

    @property
    def duration_ms(self) -> int:
        return sum(s.duration_ms for s in self.stages)


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")[:40] or "client"


def write_bundle(run: RunRecord, runs_root: Path) -> Path:
    """Write the full bundle. Returns the run directory path."""
    run_id = str(ulid.new())
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. flow.json
    flow_path = run_dir / "flow.json"
    flow_path.write_text(json.dumps(run.flow, indent=2))

    # 2. deck.pptx — also writes runs_root/<run_id>/flow.json (overwrites the
    # one above with identical content, but render_adapter expects to own it).
    suffix = "_flow_only" if run.mode == "flow_only" else ""
    deck_name = (
        f"{_slug(run.client_name)}_process_flow{suffix}"
        f"_{run.started_at:%Y-%m-%d}.pptx"
    )
    deck_path = run_dir / deck_name
    render_adapter.render_to_pptx(run.flow, deck_path, mode=run.mode)
    # render() rewrote run_dir/flow.json — restore the canonical one.
    flow_path.write_text(json.dumps(run.flow, indent=2))

    # 3. previews/*.png
    previews_dir = run_dir / "previews"
    render_adapter.render_previews(deck_path, previews_dir)

    # 4. issues.md
    issues_path = run_dir / "issues.md"
    issues_path.write_text(_render_issues(run))

    # 5. run_metadata.json
    meta_path = run_dir / "run_metadata.json"
    meta_path.write_text(json.dumps(_metadata(run, run_id, deck_name), indent=2))

    return run_dir


def _metadata(run: RunRecord, run_id: str, deck_name: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "user": run.user,
        "client_name": run.client_name,
        "vertical": run.vertical,
        "mode": run.mode,
        "model": run.model,
        "started_at": run.started_at.isoformat(),
        "duration_ms": run.duration_ms,
        "deck_filename": deck_name,
        "stages": [
            {
                "name": s.name,
                "input_tokens": s.input_tokens,
                "output_tokens": s.output_tokens,
                "ms": s.duration_ms,
            }
            for s in run.stages
        ],
        "tokens_in_total": run.total_tokens_in,
        "tokens_out_total": run.total_tokens_out,
        "repair_errors_unresolved": run.repair_errors,
    }


def _render_issues(run: RunRecord) -> str:
    lines = [
        f"# Issues & Assumptions — {run.client_name}",
        "",
        f"_Run started: {run.started_at.isoformat()}_  ",
        f"_Vertical: {run.vertical}_  ",
        f"_Model: {run.model}_",
        "",
        "## Assumptions made",
        "",
    ]
    if run.assumptions:
        lines.extend(f"- {a}" for a in run.assumptions)
    else:
        lines.append("_None recorded by the agent._")

    lines += ["", "## Stage notes", ""]
    if run.notes:
        lines.extend(f"- {n}" for n in run.notes)
    else:
        lines.append("_No additional notes._")

    if run.repair_errors:
        lines += [
            "",
            "## Schema repair — unresolved errors",
            "",
            "The following validation issues survived the repair stage. "
            "Review the JSON manually before sharing the deck:",
            "",
        ]
        lines.extend(f"- `{e}`" for e in run.repair_errors)

    lines += [
        "",
        "## How to act on this",
        "",
        "- Review each assumption above against your transcript / client knowledge.",
        "- Edit `flow.json` directly to fix anything wrong, then re-render with `pf render flow.json deck.pptx`.",
        "- To regenerate one section against an updated transcript: `pf rebuild <run_id> --section process_mapping`.",
        "",
    ]
    return "\n".join(lines)
