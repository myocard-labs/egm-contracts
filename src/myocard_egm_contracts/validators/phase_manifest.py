"""Validate a phase manifest.json against the schema.

The per-phase manifest is a JSON document (one per project phase) that
indexes every artifact in the phase as a shallow pointer. This validator
only checks one manifest file against the JSON Schema; it does NOT do the
cross-file scan-and-validate (orphan detection, cross-reference integrity,
usage-tag coverage) — that lives in
``intracardiac-platform/scripts/validate_manifest.py``, which builds on top
of this conformance check.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_phase_manifest(path: Path | str) -> ValidationResult:
    """Open a phase ``manifest.json`` file and check it against the schema."""
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ValidationResult.failing(path, [f"JSON parse failed: {e}"])

    if not isinstance(doc, dict):
        return ValidationResult.failing(
            path,
            [f"expected a JSON object at the top level, got {type(doc).__name__}"],
        )

    return validate_doc_against(doc, "phase_manifest", path)
