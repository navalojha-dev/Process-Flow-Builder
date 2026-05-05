"""Thin wrapper around the existing renderer in `.claude/skills/process-flow/render.py`.

We don't want to copy render.py — it's actively maintained for the CC
skill use case. Instead we import it via path so both the skill and
the CLI share one renderer. If the renderer signature changes, both
update together.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_RENDER_PATH = (
    Path(__file__).resolve().parent.parent
    / ".claude"
    / "skills"
    / "process-flow"
    / "render.py"
)


def _load_render_module():
    spec = importlib.util.spec_from_file_location("pf_render_skill", _RENDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load renderer from {_RENDER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pf_render_skill"] = mod
    spec.loader.exec_module(mod)
    return mod


def render_to_pptx(flow: dict, out_path: Path, *, mode: str = "full") -> Path:
    """Write `flow` to a temp JSON, call render(), return the PPTX path.

    `mode`:
      - "full"      — 3 slides: Process Flow + As-Is/To-Be/Impact + AgentFleet.
      - "flow_only" — 1 slide: Process Flow only.
    """
    mod = _load_render_module()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    flow_json = out_path.parent / "flow.json"
    flow_json.write_text(json.dumps(flow, indent=2))

    if mode == "full":
        mod.render(flow_json, out_path)
    elif mode == "flow_only":
        # Build a one-slide deck using just the Process Flow builder. We
        # don't call mod.render() because it always emits all 3 slides.
        from pptx import Presentation
        from pptx.util import Inches

        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(5.625)
        mod.render_process_flow_v2(prs, flow)
        prs.save(str(out_path))
        print(f"Wrote {out_path} (flow_only)")
    else:
        raise ValueError(f"mode must be 'full' or 'flow_only', got {mode!r}")
    return out_path


def render_previews(pptx_path: Path, out_dir: Path) -> list[Path]:
    """Convert PPTX -> 3 PNG previews using soffice + pdftoppm.

    Best-effort. If LibreOffice / pdftoppm aren't installed, returns
    [] and lets the caller carry on.
    """
    import shutil
    import subprocess

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not (shutil.which("soffice") and shutil.which("pdftoppm")):
        return []

    pdf_path = out_dir / (pptx_path.stem + ".pdf")
    subprocess.run(
        [
            "soffice", "--headless", "--convert-to", "pdf",
            str(pptx_path), "--outdir", str(out_dir),
        ],
        check=False, capture_output=True,
    )
    if not pdf_path.exists():
        return []

    stem = out_dir / "slide"
    subprocess.run(
        ["pdftoppm", "-r", "110", str(pdf_path), str(stem), "-png"],
        check=False, capture_output=True,
    )
    # Drop the intermediate PDF; we keep only the PNGs in previews/.
    pdf_path.unlink(missing_ok=True)
    return sorted(out_dir.glob("slide-*.png"))
