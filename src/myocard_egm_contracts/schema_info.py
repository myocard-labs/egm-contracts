"""Public schema introspection API — single source of truth for everything
consumers need to read off a schema at runtime.

The JSON Schemas in ``myocard_egm_contracts.schemas`` are the canonical
contract. This module reads them and exposes:

- ``current_version(name)`` — the version a producer should stamp into a
  freshly-written file (the newest entry in the schema's ``schema_version.enum``).
- ``supported_versions(name)`` — every version the schema currently accepts
  on read (the full ``schema_version.enum`` list).
- ``csv_column_order(name)`` — the contract column order for CSV outputs
  (from the ``x-csv-column-order`` extension key when present, otherwise
  the schema's ``properties`` insertion order).
- ``csv_required_columns(name)`` — the schema's ``required`` field list.
- ``field_type_map(name)`` — ``{property_name: [json-schema types]}``, used
  by readers to decide how to coerce CSV string cells back into Python
  numeric types.
- ``get_schema(name)`` — the raw JSON Schema dict, for tools that need
  something else.

Why this lives here rather than in consumers: the JSON Schemas are the
truth, and consumers should not duplicate version literals, column lists,
or type maps. If a schema's ``schema_version.enum`` adds ``"1.1"``, every
consumer that pulls through this API picks it up automatically with no
code change.

Schemas are cached after first read (they are static for the life of the
installed wheel).

Example::

    from myocard_egm_contracts.schema_info import current_version

    SYNTHETIC_BANK_VERSION = current_version("synthetic_bank")  # "1.0"
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

__all__ = [
    "csv_column_order",
    "csv_required_columns",
    "current_version",
    "field_type_map",
    "get_schema",
    "supported_versions",
]


_SCHEMAS_PACKAGE = "myocard_egm_contracts.schemas"


@cache
def get_schema(name: str) -> dict[str, Any]:
    """Load and return the raw JSON Schema dict for ``name``.

    ``name`` is the schema's base filename without the ``.schema.json``
    suffix — e.g. ``"synthetic_bank"``, ``"training_run_record"``,
    ``"egm_class_model_metadata"``.

    Raises FileNotFoundError if no schema by that name ships in the wheel.
    Result is cached; the schemas are static.
    """
    filename = f"{name}.schema.json"
    try:
        resource = resources.files(_SCHEMAS_PACKAGE).joinpath(filename)
    except ModuleNotFoundError as exc:
        raise FileNotFoundError(
            f"Schemas package {_SCHEMAS_PACKAGE!r} not found; the wheel "
            "may have been installed without its schema artifacts."
        ) from exc
    if not resource.is_file():
        raise FileNotFoundError(
            f"Schema {filename!r} not found under {_SCHEMAS_PACKAGE}. "
            "Available schemas: "
            f"{sorted(p.name for p in resources.files(_SCHEMAS_PACKAGE).iterdir() if p.is_file() and p.name.endswith('.schema.json'))}"
        )
    with resource.open(encoding="utf-8") as f:
        loaded = json.load(f)
    if not isinstance(loaded, dict):
        raise ValueError(f"Schema {filename!r} did not parse as a JSON object.")
    return loaded


def supported_versions(name: str) -> tuple[str, ...]:
    """Return every version the schema currently accepts on read.

    Pulled from the schema's ``properties.schema_version.enum``. Writers
    use the newest (last) entry; readers use the full list when checking
    a file's stamped version.

    Returns an empty tuple if the schema has no ``schema_version`` field
    (e.g. ``metrics.schema.json`` describes a single CSV row, not a
    versioned document).
    """
    entry = _schema_version_entry(name)
    if entry is None:
        return ()
    enum = entry.get("enum")
    if isinstance(enum, list):
        return tuple(str(v) for v in enum)
    const = entry.get("const")
    if const is not None:
        return (str(const),)
    return ()


def current_version(name: str) -> str:
    """The newest version of ``name`` — what a writer should stamp.

    Raises ValueError if the schema has no ``schema_version`` field.
    """
    versions = supported_versions(name)
    if not versions:
        raise ValueError(
            f"Schema {name!r} has no schema_version field. Use "
            "supported_versions() to check before calling."
        )
    return versions[-1]


def csv_column_order(name: str) -> tuple[str, ...]:
    """Contract column order for a schema describing a CSV row.

    Reads the schema's ``x-csv-column-order`` extension key when present
    (e.g. ``predictions.schema.json``). Falls back to the order of the
    schema's ``properties`` dict when the extension is missing (which
    happens for plain row-oriented schemas like ``metrics.schema.json``,
    where every property is a column and order follows the schema author's
    intent encoded in the file).

    Raises ValueError if the schema has no ``properties``.
    """
    schema = get_schema(name)
    explicit = schema.get("x-csv-column-order")
    if isinstance(explicit, list):
        return tuple(str(c) for c in explicit)
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(
            f"Schema {name!r} has neither x-csv-column-order nor a "
            "properties dict; can't infer CSV column order."
        )
    return tuple(properties.keys())


def csv_required_columns(name: str) -> frozenset[str]:
    """Set of property names the schema marks as ``required``."""
    schema = get_schema(name)
    required = schema.get("required", [])
    if not isinstance(required, list):
        return frozenset()
    return frozenset(str(c) for c in required)


def field_type_map(name: str) -> dict[str, tuple[str, ...]]:
    """``{property_name: (json-schema-types,)}`` for every top-level property.

    JSON Schema's ``type`` may be a single string (``"number"``) or a list
    (``["number", "null"]`` for nullable). This helper normalizes both
    cases to a tuple. Used by record readers (e.g. metrics.csv) to decide
    which columns to coerce to ``int`` vs ``float`` vs leave as string,
    and which can validly be ``None``.

    Properties with a ``$ref`` (the type is defined in ``$defs``) appear
    with an empty tuple — callers that need to follow $refs should call
    :func:`get_schema` and walk manually.
    """
    schema = get_schema(name)
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for prop, spec in properties.items():
        if not isinstance(spec, dict):
            out[str(prop)] = ()
            continue
        t = spec.get("type")
        if isinstance(t, str):
            out[str(prop)] = (t,)
        elif isinstance(t, list):
            out[str(prop)] = tuple(str(x) for x in t)
        else:
            out[str(prop)] = ()
    return out


def _schema_version_entry(name: str) -> dict[str, Any] | None:
    schema = get_schema(name)
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return None
    entry = properties.get("schema_version")
    if not isinstance(entry, dict):
        return None
    return entry
