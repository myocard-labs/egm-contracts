"""Validate a figure spec JSON file against the schema.

A figure spec is the declarative, git-tracked source of truth for one
publication figure; the rendered image is gitignored build output. This
validator checks one spec file against the JSON Schema. Recipe-specific
input validation (does this recipe accept these inputs?) is owned by
egm-studio's render layer, not the contract.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_figure_spec(path: Path | str) -> ValidationResult:
    """Open a figure-spec ``.json`` file and check it against the schema."""
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

    return validate_doc_against(doc, "figure_spec", path)
