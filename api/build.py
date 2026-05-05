"""Vercel serverless API endpoint — POST /api/build

Receives a JSON payload, runs the 5-stage agent pipeline, returns the
rendered PPTX as a binary download. No previews (LibreOffice isn't
available on Vercel functions). No bundle directory (we just stream
the PPTX bytes back).

Request body
------------
{
  "client":     "Aljomaih · Pepsi KSA",
  "vertical":   "fmcg-distribution",     // optional
  "transcript": "<raw meeting notes>"
}

Response
--------
- 200 + body=PPTX bytes, Content-Type=application/vnd.openxmlformats-...,
  Content-Disposition=attachment; filename="<client>_process_flow_<date>.pptx"
- 4xx / 5xx with text/plain error message

Env vars (set in Vercel project settings)
-----------------------------------------
- GEMINI_API_KEY     (required) — get one at https://aistudio.google.com/apikey
- PF_GEMINI_MODEL    (optional) — defaults to "gemini-2.5-flash"
- PF_PROVIDER        (optional) — defaults to "gemini" on Vercel
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Vercel runs `api/build.py` with the project root on sys.path. Make
# sure pf_builder imports work both there and during `vercel dev`.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Gemini is the only provider we ship to Vercel (smaller bundle, free tier).
os.environ.setdefault("PF_PROVIDER", "gemini")

from pf_builder.orchestrator import run_pipeline  # noqa: E402
from pf_builder.render_adapter import render_to_pptx  # noqa: E402


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")[:40] or "client"


class handler(BaseHTTPRequestHandler):
    """Vercel Python runtime expects a `handler` class subclassing BaseHTTPRequestHandler."""

    def _send_text(self, status: int, msg: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(msg.encode("utf-8"))

    def do_POST(self) -> None:  # noqa: N802
        # ── Read + validate body ─────────────────────────────────────
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            return self._send_text(400, "Body must be valid JSON.")

        transcript = (payload.get("transcript") or "").strip()
        client = (payload.get("client") or "").strip()
        vertical = (payload.get("vertical") or "").strip() or None
        mode = (payload.get("mode") or "full").strip().lower()

        if not transcript:
            return self._send_text(400, "Field 'transcript' is required.")
        if not client:
            return self._send_text(400, "Field 'client' is required.")
        if mode not in ("full", "flow_only"):
            return self._send_text(
                400, "Field 'mode' must be 'full' or 'flow_only'."
            )

        if not os.environ.get("GEMINI_API_KEY"):
            return self._send_text(
                500,
                "GEMINI_API_KEY is not set on the deployment. "
                "Set it in Vercel project Settings → Environment Variables.",
            )

        # ── Run agent ────────────────────────────────────────────────
        try:
            with tempfile.TemporaryDirectory() as td:
                runs_root = Path(td) / "runs"
                run_dir = run_pipeline(
                    transcript=transcript,
                    client_name=client,
                    vertical_hint=vertical,
                    user="vercel-web",
                    runs_root=runs_root,
                    mode=mode,
                )
                pptx_path = next(run_dir.glob("*.pptx"), None)
                if pptx_path is None:
                    return self._send_text(500, "Renderer returned no PPTX.")
                pptx_bytes = pptx_path.read_bytes()
        except Exception as e:  # noqa: BLE001
            err = f"Build failed: {type(e).__name__}: {e}"
            return self._send_text(500, err)

        # ── Stream PPTX back ─────────────────────────────────────────
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"{_slug(client)}_process_flow_{date}.pptx"

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        self.send_header("Content-Length", str(len(pptx_bytes)))
        self.send_header(
            "Content-Disposition", f'attachment; filename="{filename}"'
        )
        self.send_header("X-Deck-Filename", filename)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(pptx_bytes)

    def do_GET(self) -> None:  # noqa: N802
        self._send_text(
            405,
            "Method not allowed. POST a JSON body with {client, vertical, transcript}.",
        )
