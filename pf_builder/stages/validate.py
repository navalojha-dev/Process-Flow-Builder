"""Stage 5 — Schema validation + auto-repair.

Validates the assembled flow.json against the renderer's schema. Also
runs a few semantic checks the schema can't express (icon-name in
manifest, agent-name in catalog, label length sanity).

If anything fails, calls Claude once with the error list to repair
the JSON. One repair attempt — if it still fails, raise.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from ..kb.catalog import AGENTFLEET
from ..kb.icons import is_known
from ..llm import StageResult, ask_for_json

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude"
    / "skills"
    / "process-flow"
    / "schema.json"
)


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def _semantic_errors(flow: dict) -> list[str]:
    """Checks beyond JSON-schema: icon names, agent names, label lengths."""
    errors: list[str] = []

    pf = flow.get("process_flow", {})
    for r_idx, row in enumerate(pf.get("rows", [])):
        for s_idx, step in enumerate(row.get("steps", [])):
            icon = step.get("icon", "")
            if not is_known(icon):
                errors.append(
                    f"process_flow.rows[{r_idx}].steps[{s_idx}].icon "
                    f"'{icon}' is not in the manifest."
                )
            label = step.get("label", "")
            if len(label) > 60:
                errors.append(
                    f"process_flow.rows[{r_idx}].steps[{s_idx}].label is "
                    f"{len(label)} chars (>60 will overflow)."
                )

    catalog_names = {a["agent"] for a in AGENTFLEET}
    for i, card in enumerate(flow.get("ai_use_cases", [])):
        if card.get("agent") not in catalog_names:
            errors.append(
                f"ai_use_cases[{i}].agent '{card.get('agent')}' is not in "
                f"the catalog."
            )
        if len(card.get("tagline", "")) > 40:
            errors.append(
                f"ai_use_cases[{i}].tagline is too long "
                f"({len(card.get('tagline', ''))} chars; cap 40)."
            )

    return errors


def validate(flow: dict) -> list[str]:
    """Return a list of error strings. Empty = valid."""
    schema = _load_schema()
    errors: list[str] = []
    validator = jsonschema.Draft7Validator(schema)
    for err in validator.iter_errors(flow):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"{path}: {err.message}")
    errors.extend(_semantic_errors(flow))
    return errors


REPAIR_SYSTEM = """You repair a Shipsy process-flow JSON document so it matches its schema.

Input: a JSON document and a list of validation errors.
Output: a corrected JSON document inside a fenced ```json block. Make the smallest change that fixes each error. Do NOT redesign the deck.

Specific fixes you may need:
- Replace an unknown icon with a similar canonical icon from the manifest.
- Truncate over-length labels (preserve meaning).
- Drop or rename agent cards whose `agent` is not in the catalog.
- Fix missing required fields by using a sensible default from context.
"""


def repair(flow: dict, errors: list[str]) -> StageResult:
    user = (
        "VALIDATION ERRORS:\n"
        + "\n".join(f"- {e}" for e in errors)
        + "\n\nDOCUMENT TO REPAIR:\n"
        + json.dumps(flow, indent=2)
    )
    return ask_for_json(system=REPAIR_SYSTEM, user=user, max_tokens=4000)


def validate_and_repair(flow: dict) -> tuple[dict, list[str], StageResult | None]:
    """Returns (final_flow, remaining_errors, repair_call_result_or_none)."""
    errors = validate(flow)
    if not errors:
        return flow, [], None

    result = repair(flow, errors)
    repaired = result.data
    remaining = validate(repaired)
    return repaired, remaining, result
