"""Validate an observation JSON file against the schema.

An observation records a discovery during signal exploration or ML
diagnostics. Its free-text ``description`` is required; ``traces`` and
``view_state`` are optional. This validator checks one observation file
against the JSON Schema. Cross-reference integrity (do the referenced bank
ids resolve to real artifacts in the phase?) is a manifest-level concern,
handled by ``intracardiac-platform/scripts/validate_manifest.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_observation(path: Path | str) -> ValidationResult:
    """Open an observation ``.json`` file and check it against the schema."""
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

    return validate_doc_against(doc, "observation", path)
