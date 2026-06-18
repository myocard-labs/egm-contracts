"""Validate a noise bank HDF5 file against noise_bank.schema.json.

The noise_bank schema (v1.0) is intentionally minimal — only the fields
the mixer actually consumes. Extraction provenance (calibration, threshold,
windowing, per-trace audit) lives in a sibling noise_bank_run_record.json
file with its own schema and validator. See validate_noise_bank_run_record.

There is no schema-side check that the sibling exists or matches — that
convention (same directory, matching name stem) is producer-enforced.
"""

from __future__ import annotations

from pathlib import Path

import h5py

from ._hdf5 import read_group_columns, read_root_attrs
from ._result import ValidationResult
from ._schema import validate_doc_against


def validate_noise_bank(path: Path | str) -> ValidationResult:
    """Open a noise bank HDF5 file and check it against the schema."""
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

    return validate_doc_against(doc, "noise_bank", path)
