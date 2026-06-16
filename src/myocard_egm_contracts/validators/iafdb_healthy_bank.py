"""Validate an IAFDB healthy bank HDF5 file against iafdb_healthy_bank.schema.json.

Includes the cross-field consistency check that
``window_samples == round(window_ms * 1e-3 * fs_hz)``. JSON Schema can't
elegantly express this constraint; the producer writes both for
downstream convenience and the validator enforces consistency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py

from ._hdf5 import read_group_columns, read_root_attrs
from ._result import ValidationResult
from ._schema import validate_doc_against


def _cross_field_issues(doc: dict[str, Any]) -> list[str]:
    """Detect ``window_samples`` / ``window_ms`` / ``fs_hz`` inconsistencies."""
    issues: list[str] = []
    required = ("window_samples", "window_ms", "fs_hz")
    if not all(k in doc for k in required):
        return issues  # the schema will flag the missing attr separately
    try:
        expected = round(float(doc["window_ms"]) * 1e-3 * float(doc["fs_hz"]))
    except (TypeError, ValueError):
        return issues
    actual = doc["window_samples"]
    if not isinstance(actual, int):
        return issues
    if actual != expected:
        issues.append(
            f"<root>: window_samples ({actual}) does not match "
            f"round(window_ms * 1e-3 * fs_hz) = {expected}"
        )
    return issues


def validate_iafdb_healthy_bank(path: Path | str) -> ValidationResult:
    """Open an HDF5 IAFDB healthy bank and check it against the schema."""
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        with h5py.File(path, "r") as f:
            doc = read_root_attrs(f)
            if "traces" in f:
                doc["traces"] = read_group_columns(f, "traces")
    except (OSError, KeyError) as e:
        return ValidationResult.failing(path, [f"HDF5 read failed: {e}"])

    extra = _cross_field_issues(doc)
    return validate_doc_against(doc, "iafdb_healthy_bank", path, extra_issues=extra)
