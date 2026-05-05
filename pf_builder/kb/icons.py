"""Icon catalog — wraps the existing manifest used by render.py.

23 canonical icons + 73 aliases. Stages 2 (process flow) reference
icons by name; the validator uses `is_known()` to catch typos before
they hit the renderer.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# Re-use the manifest the renderer ships with so we never get out of
# sync with what render.py can actually draw.
_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude"
    / "skills"
    / "process-flow"
    / "icons"
    / "manifest.json"
)


@lru_cache(maxsize=1)
def _manifest() -> dict:
    return json.loads(_MANIFEST_PATH.read_text())


def canonical_icons() -> list[str]:
    return sorted(_manifest()["icons"])


def aliases() -> dict[str, str]:
    return dict(_manifest()["aliases"])


def is_known(name: str) -> bool:
    m = _manifest()
    return name in m["icons"] or name in m["aliases"]


def resolve(name: str) -> str | None:
    """Return the canonical icon name, or None if unknown."""
    m = _manifest()
    if name in m["icons"]:
        return name
    return m["aliases"].get(name)


def catalog_for_prompt() -> str:
    """Compact, prompt-friendly representation of the icon library.

    Stage 2 sees this verbatim. Keep it short — it's in every flow-design
    prompt and we pay tokens for every word.
    """
    canonical = canonical_icons()
    al = aliases()
    # Group aliases by what they resolve to so the model can scan quickly.
    grouped: dict[str, list[str]] = {}
    for alias, canon in al.items():
        grouped.setdefault(canon, []).append(alias)

    lines = ["CANONICAL ICONS (use these directly):"]
    for icon in canonical:
        extra = ", ".join(sorted(grouped.get(icon, []))[:4])
        if extra:
            lines.append(f"  - {icon}   (aliases: {extra}…)")
        else:
            lines.append(f"  - {icon}")
    return "\n".join(lines)
