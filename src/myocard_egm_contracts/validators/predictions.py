"""Validate a predictions manifest (predictions_<eval>.json)."""

from __future__ import annotations

import json
from pathlib import Path

from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_predictions(path: Path | str) -> ValidationResult:
    """Open a predictions manifest JSON and check it against the schema.

    The paired CSV is not validated here — the contract is that the CSV
    column order matches ``columns`` in the manifest. A future
    ``validate_predictions_pair(json_path, csv_path)`` could enforce
    that, but the v1 helper only handles the manifest.
    """
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ValidationResult.failing(path, [f"JSON parse failed: {e}"])

    return validate_doc_against(doc, "predictions", path)
