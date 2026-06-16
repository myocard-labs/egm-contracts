"""Validate a synthetic bank HDF5 file against synthetic_bank.schema.json."""

from __future__ import annotations

from pathlib import Path

import h5py

from ._hdf5 import read_group_columns, read_root_attrs
from ._result import ValidationResult
from ._schema import validate_doc_against

# The four root attrs the producer writes as JSON-encoded strings; the
# schema expects them as nested objects. The mapping decodes them.
_JSON_ENCODED_ATTRS = {
    "fibrosis_params_json": "fibrosis_params",
    "electrode_config_json": "electrode_config",
    "mixer_config_json": "mixer_config",
    "experiment_config_json": "experiment_config",
}


def validate_synthetic_bank(path: Path | str) -> ValidationResult:
    """Open an HDF5 synthetic bank and check it against the schema."""
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        with h5py.File(path, "r") as f:
            doc = read_root_attrs(f, json_encoded=_JSON_ENCODED_ATTRS)
            if "traces" in f:
                doc["traces"] = read_group_columns(f, "traces")
    except (OSError, KeyError) as e:
        return ValidationResult.failing(path, [f"HDF5 read failed: {e}"])

    return validate_doc_against(doc, "synthetic_bank", path)
