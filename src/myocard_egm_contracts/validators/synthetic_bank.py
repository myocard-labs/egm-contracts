"""Validate a synthetic bank HDF5 file against synthetic_bank.schema.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py

from ._hdf5 import read_group_columns, read_json_columns, read_root_attrs
from ._result import ValidationResult
from ._schema import validate_doc_against

# The one root attr the producer writes as a JSON-encoded string; the schema
# expects the decoded object. (2.0 dropped 1.1's four config attrs — that
# per-simulation detail now lives in the `simulations/` group instead.)
_JSON_ENCODED_ATTRS = {"generation_params_json": "generation_params"}


def _orphan_simulation_ids(doc: dict[str, Any]) -> list[str]:
    """Check every trace's simulation_id resolves in the simulations group.

    JSON Schema cannot express a reference between two sibling groups, so the
    foreign key that holds the whole 2.0 restructure together — trace →
    simulation — would otherwise go unchecked. An orphan is a trace whose
    generation config cannot be recovered, which is precisely the failure the
    restructure exists to make impossible.
    """
    simulations = doc.get("simulations")
    traces = doc.get("traces")
    if not isinstance(simulations, dict) or not isinstance(traces, dict):
        return []  # shape errors are the schema's to report

    known = simulations.get("simulation_id")
    referenced = traces.get("simulation_id")
    if not isinstance(known, list) or not isinstance(referenced, list):
        return []

    missing = sorted({sid for sid in referenced if sid not in set(known)})
    if not missing:
        return []
    shown = ", ".join(str(m) for m in missing[:5])
    suffix = " ..." if len(missing) > 5 else ""
    return [
        f"traces/simulation_id: {len(missing)} id(s) absent from "
        f"simulations/simulation_id: [{shown}{suffix}]"
    ]


def validate_synthetic_bank(path: Path | str) -> ValidationResult:
    """Open an HDF5 synthetic bank and check it against the schema."""
    path = Path(path)
    if not path.exists():
        return ValidationResult.failing(path, [f"file not found: {path}"])

    try:
        with h5py.File(path, "r") as f:
            doc: dict[str, Any] = read_root_attrs(f, json_encoded=_JSON_ENCODED_ATTRS)
            if "simulations" in f:
                doc["simulations"] = read_json_columns(read_group_columns(f, "simulations"))
            if "traces" in f:
                doc["traces"] = read_group_columns(f, "traces")
    except (OSError, KeyError) as e:
        return ValidationResult.failing(path, [f"HDF5 read failed: {e}"])

    return validate_doc_against(
        doc, "synthetic_bank", path, extra_issues=_orphan_simulation_ids(doc)
    )
