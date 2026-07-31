"""Tests for the shared ``$defs`` in common.schema.json that aren't ID patterns.

The ID patterns (ArtifactId / FigureId / PaperId) are covered in
test_linkage_schemas.py; this module covers the other cross-schema
definitions. Today that means ``ActivationPosition`` — the [0,1] activation
fraction stored by both ``iafdb_bank`` and ``synthetic_bank``, defined once
here so the two corpora cannot drift (the comparison STU5 makes is only
meaningful if both sides mean the same thing by the number).
"""

from __future__ import annotations

from typing import Any

import jsonschema
import pytest

from myocard_egm_contracts.schema_info import get_schema

# Schemas that carry (or will carry) an ActivationPosition $ref. Kept explicit
# so a new consumer is a deliberate addition rather than an accident.
_POSITION_SCHEMAS = ("iafdb_bank", "synthetic_bank")


def _activation_position_def() -> dict[str, Any]:
    defs = get_schema("common").get("$defs", {})
    assert "ActivationPosition" in defs, "common.$defs.ActivationPosition missing"
    result: dict[str, Any] = defs["ActivationPosition"]
    return result


def test_activation_position_is_a_bounded_fraction() -> None:
    """It's a fraction of the trace, so the bounds are the contract."""
    schema = _activation_position_def()
    assert schema["type"] == "number"
    assert schema["minimum"] == 0
    assert schema["maximum"] == 1


@pytest.mark.parametrize("value", [0, 0.0, 0.25, 0.5, 1, 1.0])
def test_activation_position_accepts_in_range_values(value: float) -> None:
    """Both endpoints are legal: an activation may sit on the first or last sample."""
    jsonschema.Draft202012Validator(_activation_position_def()).validate(value)


@pytest.mark.parametrize("value", [-0.001, 1.001, 2, -1])
def test_activation_position_rejects_out_of_range_values(value: float) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(_activation_position_def()).validate(value)


def test_activation_position_rejects_non_numeric() -> None:
    """Guard against a producer writing the string form of the fraction."""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(_activation_position_def()).validate("0.5")


def test_run_record_no_longer_advertises_host() -> None:
    """B15 is convention-only — there is no `host` field to delete, just the
    well-known-key list that told producers to write one. The list *is* the
    contract, so this guards it: a future edit that reinstates the key would
    otherwise be invisible to every other test in the suite.
    """
    run_desc = get_schema("training_run_record")["properties"]["run"]["description"]
    # The description has two parts: the well-known-key list, then a NOTE
    # explaining the removal. `host` must be absent from the first and named
    # in the second — checking the whole string would pass on either.
    key_list, _, removal_note = run_desc.partition("NOTE (1.2)")
    assert removal_note, "the 1.2 removal note is gone from the run description"
    assert "'host'" not in key_list, "host is back in the well-known run keys"
    assert "SHOULD NOT" in removal_note, "the note no longer tells producers to omit it"


def test_activation_position_not_redefined_locally() -> None:
    """Single-source guard, the same rule the ID patterns follow.

    A local copy in a bank schema is how the two corpora would silently
    diverge — the failure mode that produced the sim_id / simulation_id
    split. Enforced from the moment the $def exists, not once it has
    consumers.
    """
    for name in _POSITION_SCHEMAS:
        local_defs = get_schema(name).get("$defs", {})
        assert "ActivationPosition" not in local_defs, (
            f"{name} defines ActivationPosition locally; $ref common.schema.json instead"
        )
