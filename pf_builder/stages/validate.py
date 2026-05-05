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
    """Checks beyond JSON-schema: icon names, agent names, label lengths.

    Defensive against the LLM returning the wrong shape (e.g. a list of
    strings where we expected a list of objects). Every isinstance() check
    that fails becomes a validation error the repair stage can fix —
    never an unhandled crash.
    """
    errors: list[str] = []

    # ── process_flow.rows[].steps[] ──────────────────────────────────
    pf = flow.get("process_flow", {})
    if not isinstance(pf, dict):
        errors.append(
            f"process_flow is {type(pf).__name__}, expected object."
        )
        pf = {}
    rows = pf.get("rows", [])
    if not isinstance(rows, list):
        errors.append(
            f"process_flow.rows is {type(rows).__name__}, expected array."
        )
        rows = []
    for r_idx, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(
                f"process_flow.rows[{r_idx}] is {type(row).__name__}, "
                f"expected object."
            )
            continue
        steps = row.get("steps", [])
        if not isinstance(steps, list):
            errors.append(
                f"process_flow.rows[{r_idx}].steps is "
                f"{type(steps).__name__}, expected array."
            )
            continue
        for s_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(
                    f"process_flow.rows[{r_idx}].steps[{s_idx}] is "
                    f"{type(step).__name__}, expected object with "
                    f"`label` and `icon`."
                )
                continue
            icon = step.get("icon", "")
            if not is_known(icon):
                errors.append(
                    f"process_flow.rows[{r_idx}].steps[{s_idx}].icon "
                    f"'{icon}' is not in the manifest."
                )
            label = step.get("label", "")
            if isinstance(label, str) and len(label) > 60:
                errors.append(
                    f"process_flow.rows[{r_idx}].steps[{s_idx}].label is "
                    f"{len(label)} chars (>60 will overflow)."
                )

    # ── ai_use_cases[] ───────────────────────────────────────────────
    catalog_names = {a["agent"] for a in AGENTFLEET}
    cards = flow.get("ai_use_cases", [])
    if not isinstance(cards, list):
        errors.append(
            f"ai_use_cases is {type(cards).__name__}, expected array of objects."
        )
        cards = []
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            errors.append(
                f"ai_use_cases[{i}] is {type(card).__name__} (value: "
                f"{str(card)[:40]!r}), expected object with `agent`, "
                f"`tagline`, `scenario`, `phase`."
            )
            continue
        agent = card.get("agent")
        if agent not in catalog_names:
            errors.append(
                f"ai_use_cases[{i}].agent '{agent}' is not in the catalog."
            )
        tagline = card.get("tagline", "")
        if isinstance(tagline, str) and len(tagline) > 40:
            errors.append(
                f"ai_use_cases[{i}].tagline is too long "
                f"({len(tagline)} chars; cap 40)."
            )

    # ── process_mapping[] ────────────────────────────────────────────
    mapping = flow.get("process_mapping", [])
    if not isinstance(mapping, list):
        errors.append(
            f"process_mapping is {type(mapping).__name__}, expected array."
        )
        mapping = []
    for i, row in enumerate(mapping):
        if not isinstance(row, dict):
            errors.append(
                f"process_mapping[{i}] is {type(row).__name__}, "
                f"expected object with `process`, `as_is`, `to_be`, `impact`."
            )
            continue
        for field in ("as_is", "to_be", "impact"):
            val = row.get(field)
            if val is not None and not isinstance(val, list):
                errors.append(
                    f"process_mapping[{i}].{field} is {type(val).__name__}, "
                    f"expected array of bullets."
                )

    return errors


def validate(flow: dict, *, mode: str = "full") -> list[str]:
    """Return a list of error strings. Empty = valid.

    `mode="flow_only"` skips the JSON-schema check (because the schema
    requires non-empty `process_mapping` and `ai_use_cases`, which are
    intentionally empty in flow-only runs). Semantic checks still run.
    """
    errors: list[str] = []
    if mode == "full":
        schema = _load_schema()
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


def validate_and_repair(
    flow: dict, *, mode: str = "full"
) -> tuple[dict, list[str], StageResult | None]:
    """Returns (final_flow, remaining_errors, repair_call_result_or_none)."""
    errors = validate(flow, mode=mode)
    if not errors:
        return flow, [], None

    result = repair(flow, errors)
    repaired = result.data
    remaining = validate(repaired, mode=mode)
    return repaired, remaining, result
