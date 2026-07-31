"""HDF5 → JSON-Schema-shape mapping helpers for bank validators.

The bank schemas are written as if the file were a JSON document with
top-level fields for each HDF5 root attr plus a `traces` object holding
the per-trace columns. These helpers turn an actual HDF5 file into that
shape so the generic JSON-Schema validator can run against it.

Two HDF5 idioms get translated here:

- **vlen UTF-8 strings as bytes.** h5py returns string scalars as bytes
  unless ``.asstr()`` is used; we decode consistently.
- **JSON-encoded string attrs.** The synthetic bank stores nested
  sub-configs (fibrosis_params, electrode_config, mixer_config,
  experiment_config) as JSON-stringified strings under attr names with
  a ``_json`` suffix. The mapping table tells the helper to parse them
  back into dicts before validation.
"""

from __future__ import annotations

import json
from typing import Any

import h5py
import numpy as np


def _decode_attr_value(value: Any) -> Any:
    """Normalize an HDF5 attribute value for JSON Schema validation.

    Rules:
    - bytes → utf-8 string
    - numpy scalar → Python scalar
    - numpy 1d array of bytes → list of strings
    - numpy 1d array of numbers → list of numbers
    - everything else → returned as-is
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.generic):  # numpy scalar
        return value.item()
    if isinstance(value, np.ndarray):
        if value.dtype == object:
            return [(v.decode("utf-8") if isinstance(v, bytes) else v) for v in value.tolist()]
        return value.tolist()
    return value


def read_root_attrs(
    f: h5py.File,
    *,
    json_encoded: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Read HDF5 root attrs into a dict, optionally decoding JSON-string attrs.

    Parameters
    ----------
    f
        Open h5py File handle (read mode).
    json_encoded
        Optional mapping ``{hdf5_attr_name: schema_field_name}`` that tells
        the helper to ``json.loads`` the named attrs (which are stored as
        JSON-encoded strings on disk) and emit them under the schema field
        name. The original HDF5 attr is dropped from the output.

    Returns
    -------
    dict
        ``{schema_field: value}`` ready for JSON Schema validation.
    """
    json_encoded = json_encoded or {}
    out: dict[str, Any] = {}
    for attr_name in f.attrs:
        value = _decode_attr_value(f.attrs[attr_name])
        if attr_name in json_encoded:
            try:
                parsed = json.loads(value) if isinstance(value, str) else value
            except json.JSONDecodeError:
                # If the JSON attr is malformed, surface it as the schema field
                # so the validator complains about the wrong type.
                parsed = value
            out[json_encoded[attr_name]] = parsed
        else:
            out[attr_name] = value
    return out


def read_json_columns(
    columns: dict[str, list[Any]],
    *,
    suffix: str = "_json",
) -> dict[str, list[Any]]:
    """Decode per-row JSON-string columns, stripping the ``_json`` suffix.

    The synthetic bank's ``simulations/`` group stores one typed object per
    simulation as a JSON string — ``geometry_json``, ``activation_json``, and
    so on — because HDF5 has no nested-record type worth using here and the
    objects are polymorphic. The schema describes the *decoded* form under the
    unsuffixed name, so this bridges the two.

    A row that fails to parse is left as its raw string rather than raising:
    the validator then reports "expected object, got string" against the
    offending column, which points at the problem far better than a
    JSONDecodeError raised from inside the reader.
    """
    out: dict[str, list[Any]] = {}
    for name, values in columns.items():
        if not name.endswith(suffix):
            out[name] = values
            continue
        decoded: list[Any] = []
        for value in values:
            try:
                decoded.append(json.loads(value) if isinstance(value, str) else value)
            except json.JSONDecodeError:
                decoded.append(value)
        out[name[: -len(suffix)]] = decoded
    return out


def read_group_columns(f: h5py.File, group: str = "traces") -> dict[str, list[Any]]:
    """Read every dataset in ``group`` into a dict of Python lists.

    Decodes vlen-UTF-8 string columns via ``.asstr()``. Number columns
    are emitted as nested lists for multi-dim arrays (e.g. the 2D ``signal``
    column on a bank becomes ``list[list[float]]``).

    This is the shape JSON Schema expects: ``traces`` as an object whose
    keys are column names and whose values are arrays.
    """
    out: dict[str, list[Any]] = {}
    g = f[group]
    for name in g:
        ds = g[name]
        if h5py.check_string_dtype(ds.dtype):
            out[name] = [str(v) for v in ds.asstr()[...]]
        else:
            arr = ds[...]
            if isinstance(arr, np.ndarray):
                out[name] = arr.tolist()
            else:
                out[name] = list(arr)
    return out
