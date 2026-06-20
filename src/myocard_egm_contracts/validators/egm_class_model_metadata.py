"""Validate a model metadata JSON sidecar against egm_class_model_metadata.schema.json."""

from __future__ import annotations

import json
from pathlib import Path

from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_egm_class_model_metadata(path: Path | str) -> ValidationResult:
    """Open an EGM-classifier model_metadata.json sidecar and check the schema."""
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ValidationResult.failing(path, [f"JSON parse failed: {e}"])

    return validate_doc_against(doc, "egm_class_model_metadata", path)
