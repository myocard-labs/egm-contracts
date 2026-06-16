"""Validate a metrics.csv file against metrics.schema.json (row by row)."""

from __future__ import annotations

import csv
from pathlib import Path

from ._result import ValidationResult
from ._schema import _path_str, _validator_for

_INT_COLUMNS = frozenset({"epoch"})


def _coerce_row(row: dict[str, str]) -> dict[str, object]:
    """Convert CSV string values to typed values that match the schema.

    Empty cells map to None (the JSON-null counterpart). All other numeric
    columns are floats; ``epoch`` is an int.
    """
    out: dict[str, object] = {}
    for key, value in row.items():
        if key is None:  # pragma: no cover — DictReader places extras under None key
            continue
        if value == "":
            out[key] = None
            continue
        if key in _INT_COLUMNS:
            try:
                out[key] = int(value)
            except ValueError:
                out[key] = value  # let the schema flag the type mismatch
        else:
            try:
                out[key] = float(value)
            except ValueError:
                out[key] = value
    return out


def validate_metrics(path: Path | str) -> ValidationResult:
    """Open metrics.csv and check every row against the schema."""
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    issues: list[str] = []
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            validator = _validator_for("metrics")
            for row_number, row in enumerate(reader, start=1):
                doc = _coerce_row(row)
                for err in validator.iter_errors(doc):
                    issues.append(
                        f"row {row_number}, {_path_str(err.absolute_path)}: {err.message}"
                    )
    except OSError as e:
        return ValidationResult.failing(path, [f"CSV read failed: {e}"])

    if issues:
        return ValidationResult.failing(path, issues)
    return ValidationResult.passing(path)
