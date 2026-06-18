"""Validate a noise_bank_run_record.json sidecar against the schema.

The run record is a separate file from the bank itself; this validator
only checks the JSON document. There is no cross-file check that the
record matches the sibling bank (the convention is positional: same
directory, matching name stem). A future producer-side audit tool may
add that cross-check, but it lives outside the schema layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_noise_bank_run_record(path: Path | str) -> ValidationResult:
    """Open a noise_bank_run_record.json file and check it against the schema.

    Also enforces the cross-field invariant
    ``windowing.window_samples == round(windowing.window_ms * 1e-3 * fs_hz)``,
    matching the corresponding check on iafdb_bank / noise_bank HDF5 files.
    """
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return ValidationResult.failing(path, [f"JSON parse failed: {e}"])

    result = validate_doc_against(doc, "noise_bank_run_record", path)
    if not result.ok:
        return result

    # Cross-field: windowing.window_samples must equal the derived value.
    try:
        fs_hz = float(doc["fs_hz"])
        window_ms = float(doc["windowing"]["window_ms"])
        window_samples = int(doc["windowing"]["window_samples"])
    except (KeyError, TypeError, ValueError):
        # Schema already failed for any missing/malformed field, but defend
        # against the schema-passes-yet-fields-are-wrong-type case.
        return result

    expected = round(window_ms * 1e-3 * fs_hz)
    if window_samples != expected:
        return ValidationResult.failing(
            path,
            [
                f"windowing.window_samples ({window_samples}) does not match "
                f"round(window_ms * 1e-3 * fs_hz) = "
                f"round({window_ms} * 1e-3 * {fs_hz}) = {expected}"
            ],
        )
    return result
