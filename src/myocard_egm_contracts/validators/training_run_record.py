"""Validate a run.json file against training_run_record.schema.json."""

from __future__ import annotations

import json
from pathlib import Path

from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_training_run_record(path: Path | str) -> ValidationResult:
    """Open run.json and check it against the training_run_record schema."""
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ValidationResult.failing(path, [f"JSON parse failed: {e}"])

    return validate_doc_against(doc, "training_run_record", path)
