"""Validate an IAFDB bank HDF5 file against iafdb_bank.schema.json."""

from __future__ import annotations

from pathlib import Path

import h5py

from ._hdf5 import read_group_columns, read_root_attrs
from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_iafdb_bank(path: Path | str) -> ValidationResult:
    """Open an IAFDB bank HDF5 file and check it against the schema.

    Also enforces the cross-field rule
    ``window_samples == round(window_ms * 1e-3 * fs_hz)`` — JSON Schema
    can't express this constraint directly, but it's a producer-side
    invariant that a downstream loader would otherwise discover the hard
    way.
    """
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        with h5py.File(path, "r") as f:
            doc = read_root_attrs(f)
            if "traces" in f:
                doc["traces"] = read_group_columns(f, "traces")
            fs_hz = float(f.attrs.get("fs_hz", 0))
            window_ms = float(f.attrs.get("window_ms", 0))
            window_samples = int(f.attrs.get("window_samples", 0))
    except (OSError, KeyError) as e:
        return ValidationResult.failing(path, [f"HDF5 read failed: {e}"])

    result = validate_doc_against(doc, "iafdb_bank", path)
    if not result.ok:
        return result

    expected_window_samples = round(window_ms * 1e-3 * fs_hz)
    if window_samples != expected_window_samples:
        return ValidationResult.failing(
            path,
            [
                f"window_samples ({window_samples}) does not match "
                f"round(window_ms * 1e-3 * fs_hz) = "
                f"round({window_ms} * 1e-3 * {fs_hz}) = "
                f"{expected_window_samples}"
            ],
        )
    return result
