"""`pf` — command-line entry point for the Process Flow Builder.

Subcommands:
    pf build <transcript> --client <name> [--vertical <hint>]   # full pipeline
    pf render <flow.json> [--out deck.pptx]                     # JSON -> PPTX
    pf validate <flow.json>                                     # schema + semantic check
    pf rebuild <run_id> --section <name>                        # regenerate one stage

For everything except `pf build` (and `pf rebuild`), no API key is needed —
those operate purely on existing JSON.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import render_adapter
from .bundle import RunRecord, write_bundle
from .orchestrator import run_pipeline
from .scanner import codebase as scanner
from .stages import validate

console = Console()


def _find_repo_root() -> Path:
    """The repo root is the parent of the `pf_builder` package directory."""
    return Path(__file__).resolve().parents[1]


# Best-effort .env loader. We don't want a hard dotenv dep — if it's not
# installed, the CLI still works using whatever env vars the shell exports.
def _load_dotenv_if_present() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        return
    repo = _find_repo_root()
    for candidate in (repo / ".env", Path.cwd() / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


_load_dotenv_if_present()


def _open_native(path: Path) -> None:
    if platform.system() == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif platform.system() == "Windows":  # pragma: no cover
        os.startfile(str(path))  # type: ignore[attr-defined]


@click.group()
@click.version_option()
def cli() -> None:
    """Shipsy Process Flow Builder."""


# ---------------------------------------------------------------------------
# pf build
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("transcript_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--client", "client_name", required=True, help="Client name, e.g. 'DP World Logistics'")
@click.option(
    "--vertical",
    "vertical_hint",
    default=None,
    help=(
        "Optional vertical hint. One of: fmcg-distribution, container-drayage, "
        "post-and-parcel, pallet-network, q-commerce, 3pl-cross-border, "
        "cold-chain, other."
    ),
)
@click.option(
    "--provider",
    type=click.Choice(["anthropic", "gemini"], case_sensitive=False),
    default=None,
    help=(
        "LLM provider. Defaults to PF_PROVIDER env var, then 'anthropic'. "
        "Anthropic needs ANTHROPIC_API_KEY; Gemini needs GEMINI_API_KEY."
    ),
)
@click.option(
    "--runs-dir",
    type=click.Path(file_okay=False),
    default=None,
    help="Where to write run bundles. Defaults to <repo>/outputs/runs/.",
)
@click.option("--no-open", is_flag=True, help="Don't auto-open the PPTX after build.")
def build(
    transcript_path: str,
    client_name: str,
    vertical_hint: str | None,
    provider: str | None,
    runs_dir: str | None,
    no_open: bool,
) -> None:
    """Run the full pipeline on a transcript file."""
    # Resolve provider — flag wins over env var, default 'anthropic'.
    chosen = (provider or os.environ.get("PF_PROVIDER", "anthropic")).lower()
    if chosen == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise click.ClickException(
            "ANTHROPIC_API_KEY is not set. Export it before running `pf build` "
            "with --provider anthropic, or pass --provider gemini if you have GEMINI_API_KEY."
        )
    if chosen == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        raise click.ClickException(
            "GEMINI_API_KEY is not set. Get one at https://aistudio.google.com/apikey "
            "and `export GEMINI_API_KEY=...`, or pass --provider anthropic."
        )
    # Make the chosen provider visible to every stage.
    os.environ["PF_PROVIDER"] = chosen
    console.print(f"[dim]Provider: {chosen}[/dim]")

    transcript = Path(transcript_path).read_text()
    runs_root = Path(runs_dir) if runs_dir else _find_repo_root() / "outputs" / "runs"

    def _progress(msg: str) -> None:
        console.print(f"[cyan]→[/cyan] {msg}")

    user = os.environ.get("USER", "unknown")
    run_dir = run_pipeline(
        transcript=transcript,
        client_name=client_name,
        vertical_hint=vertical_hint,
        user=user,
        runs_root=runs_root,
        progress=_progress,
    )

    _print_summary(run_dir)
    if not no_open:
        pptx = next(run_dir.glob("*.pptx"), None)
        if pptx:
            _open_native(pptx)


def _print_summary(run_dir: Path) -> None:
    meta = json.loads((run_dir / "run_metadata.json").read_text())
    table = Table(title=f"Run {meta['run_id']}", show_lines=False)
    table.add_column("Stage")
    table.add_column("In", justify="right")
    table.add_column("Out", justify="right")
    table.add_column("ms", justify="right")
    for s in meta["stages"]:
        table.add_row(s["name"], str(s["input_tokens"]), str(s["output_tokens"]), str(s["ms"]))
    table.add_row(
        "TOTAL",
        str(meta["tokens_in_total"]),
        str(meta["tokens_out_total"]),
        str(meta["duration_ms"]),
        style="bold",
    )
    console.print(table)
    console.print(f"\n[bold green]✓[/bold green] Bundle: {run_dir}")
    console.print(f"  Deck:    {run_dir / meta['deck_filename']}")
    console.print(f"  JSON:    {run_dir / 'flow.json'}")
    console.print(f"  Issues:  {run_dir / 'issues.md'}")
    previews = list((run_dir / "previews").glob("slide-*.png"))
    if previews:
        console.print(f"  Previews: {len(previews)} PNG files in {run_dir / 'previews'}")
    if meta["repair_errors_unresolved"]:
        console.print(
            f"\n[yellow]⚠ {len(meta['repair_errors_unresolved'])} validation "
            f"issues could not be auto-repaired — see issues.md[/yellow]"
        )


# ---------------------------------------------------------------------------
# pf render — JSON -> PPTX, no LLM
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("flow_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Output PPTX path. Defaults to outputs/<client>_process_flow.pptx.",
)
@click.option("--no-open", is_flag=True, help="Don't auto-open after render.")
def render(flow_path: str, out_path: str | None, no_open: bool) -> None:
    """Render a flow.json to PPTX (no LLM calls)."""
    flow = json.loads(Path(flow_path).read_text())
    if out_path is None:
        client_short = flow.get("client", {}).get("short", "deck")
        slug = "".join(c if c.isalnum() else "_" for c in client_short).strip("_")
        out_path = str(_find_repo_root() / "outputs" / f"{slug}_process_flow.pptx")
    out = render_adapter.render_to_pptx(flow, Path(out_path))
    console.print(f"[green]✓[/green] Wrote {out}")
    if not no_open:
        _open_native(out)


# ---------------------------------------------------------------------------
# pf validate — schema + semantic check, no LLM
# ---------------------------------------------------------------------------

@cli.command("validate")
@click.argument("flow_path", type=click.Path(exists=True, dir_okay=False))
def validate_cmd(flow_path: str) -> None:
    """Validate a flow.json against the schema + semantic rules."""
    flow = json.loads(Path(flow_path).read_text())
    errors = validate.validate(flow)
    if not errors:
        console.print("[green]✓[/green] flow.json is valid.")
        return
    console.print(f"[red]✗[/red] {len(errors)} issue(s):")
    for e in errors:
        console.print(f"  - {e}")
    raise click.exceptions.Exit(code=1)


# ---------------------------------------------------------------------------
# pf dry-run — exercise the renderer + bundle writer with a fixture flow.json
# ---------------------------------------------------------------------------

@cli.command("dry-run")
@click.argument("flow_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--client",
    "client_name",
    default=None,
    help="Override client name (defaults to client.name in the flow JSON).",
)
def dry_run(flow_path: str, client_name: str | None) -> None:
    """Exercise the bundle writer end-to-end without any LLM calls.

    Useful to verify the renderer + previews + bundle layout work on a
    teammate's machine before they spend a token. Reads an existing
    flow.json (e.g. one of /tmp/pf_runs/*.json) and writes a fake run
    bundle to outputs/runs/.
    """
    import datetime as dt

    flow = json.loads(Path(flow_path).read_text())
    name = client_name or flow.get("client", {}).get("name", "Dry Run")
    run = RunRecord(
        user=os.environ.get("USER", "unknown"),
        client_name=name,
        vertical=flow.get("client", {}).get("vertical", "other"),
        mode="dry-run",
        flow=flow,
        assumptions=["Dry-run: no LLM was called. Bundle uses the supplied JSON verbatim."],
        notes=[],
        repair_errors=validate.validate(flow),
        started_at=dt.datetime.now(dt.timezone.utc),
        model="(none)",
    )
    runs_root = _find_repo_root() / "outputs" / "runs"
    run_dir = write_bundle(run, runs_root)
    _print_summary(run_dir)


# ---------------------------------------------------------------------------
# pf scan-codebase — produces .kb-cache/codebase-features.json for Stage 5
# ---------------------------------------------------------------------------

@cli.command("scan-codebase")
@click.argument(
    "repo_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Output JSON path. Defaults to <repo>/.kb-cache/codebase-features.json.",
)
def scan_codebase_cmd(repo_root: str, out_path: str | None) -> None:
    """Scan a Shipsy codebase and write a feature manifest.

    Pure read — never executes the codebase. Walks top-level modules,
    common/models, agents/, common/devrev, package.json, db_migrations,
    and grep-extracts API endpoints. Output feeds Stage 5 validation:
    the agent's to-be bullets are checked against this manifest before
    the deck ships.
    """
    root = Path(repo_root)
    console.print(f"[cyan]Scanning[/cyan] {root}")
    manifest = scanner.scan(root)

    if out_path is None:
        out = _find_repo_root() / ".kb-cache" / "codebase-features.json"
    else:
        out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, default=str))

    s = manifest["summary"]
    table = Table(title="Scan summary", show_lines=False)
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    for k, v in s.items():
        table.add_row(k, str(v))
    console.print(table)
    console.print(f"\n[green]✓[/green] Wrote {out}")


if __name__ == "__main__":
    cli()
