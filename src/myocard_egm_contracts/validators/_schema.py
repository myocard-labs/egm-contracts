"""Shared helpers: JSON Schema loading + generic dict validation."""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource

from ._result import ValidationResult


@cache
def _load_schema(name: str) -> dict[str, Any]:
    """Load a JSON Schema file from the schemas/ package data.

    Cached: schemas don't change at runtime; loading them once per process
    is plenty.
    """
    schema_text = (
        resources.files("myocard_egm_contracts.schemas") / f"{name}.schema.json"
    ).read_text(encoding="utf-8")
    result: dict[str, Any] = json.loads(schema_text)
    return result


@cache
def _registry() -> Registry:
    """A referencing Registry holding every schema in the package, keyed by $id.

    Needed so cross-file ``$ref``s resolve — e.g. a schema's ``bank_id``
    field references ``common.schema.json#/$defs/ArtifactId``, where the
    stable-ID patterns are defined exactly once. Cached for the process.
    """
    entries: list[tuple[str, Resource[Any]]] = []
    for entry in resources.files("myocard_egm_contracts.schemas").iterdir():
        if entry.name.endswith(".schema.json"):
            schema = json.loads(entry.read_text(encoding="utf-8"))
            entries.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(entries)


def _validator_for(name: str) -> jsonschema.Draft202012Validator:
    """Build a Draft 2020-12 validator for the named schema.

    The validator carries the package-wide :func:`_registry` so cross-file
    ``$ref``s into ``common.schema.json`` resolve.
    """
    schema = _load_schema(name)
    return jsonschema.Draft202012Validator(schema, registry=_registry())


def _path_str(path: tuple[Any, ...] | list[Any]) -> str:
    """Format a jsonschema error path (e.g., ('traces', 'signal', 0)) as a path string."""
    if not path:
        return "<root>"
    return "/".join(str(p) for p in path)


def validate_doc_against(
    doc: dict[str, Any],
    schema_name: str,
    path: Path,
    extra_issues: list[str] | None = None,
) -> ValidationResult:
    """Run jsonschema validation of ``doc`` against the named schema.

    ``extra_issues`` lets a caller pre-populate cross-field issues that
    aren't expressible in JSON Schema (e.g., the IAFDB bank's
    ``window_samples == round(window_ms * 1e-3 * fs_hz)`` consistency
    check). They're prepended to whatever the schema validator reports.
    """
    validator = _validator_for(schema_name)
    schema_issues = [
        f"{_path_str(e.absolute_path)}: {e.message}" for e in validator.iter_errors(doc)
    ]
    all_issues = list(extra_issues or []) + schema_issues
    if all_issues:
        return ValidationResult.failing(path, all_issues)
    return ValidationResult.passing(path)
