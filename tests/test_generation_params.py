"""Tests for generation_params.schema.json — the bank-scoped theta-spec.

Separate from test_simulation_config.py because the two schemas have different
scopes: simulation_config describes ONE simulation, this describes the sweep
that produced many. The tests below lean on that distinction — most of what
they assert is about what the theta-spec deliberately does NOT store.
"""

from __future__ import annotations

from typing import Any

import jsonschema
import pytest
from referencing import Registry, Resource

from myocard_egm_contracts.schema_info import get_schema

_SCHEMA_NAME = "generation_params"


def _validator(def_name: str) -> jsonschema.Draft202012Validator:
    """Build a validator for one ``$def``, the way synthetic_bank references it."""
    schema = get_schema(_SCHEMA_NAME)
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return jsonschema.Draft202012Validator(
        {"$ref": f"{schema['$id']}#/$defs/{def_name}"}, registry=registry
    )


def test_theta_spec_is_bank_scoped_not_simulation_scoped() -> None:
    """Scope guard. The theta-spec is a per-BANK record of what a sweep varied;
    the per-simulation config is a different schema. They were briefly in one
    file, which made the boundary invisible — this keeps them apart."""
    assert "GenerationParams" not in get_schema("simulation_config")["$defs"]
    assert "TunedParam" not in get_schema("simulation_config")["$defs"]
    assert set(get_schema(_SCHEMA_NAME)["$defs"]) == {"TunedParam", "GenerationParams"}


WAVE1_THETA_SPEC: dict[str, Any] = {
    "regime": {
        "geometry": "patch_2d",
        "cell_model": "courtemanche",
        "substrate": "uniform_random_fibrosis",
    },
    "knobs": [],
}
SWEEP_THETA_SPEC: dict[str, Any] = {
    "regime": {"cell_model": "courtemanche", "substrate": "uniform_random_fibrosis"},
    "knobs": [
        {
            "path": "substrate.density",
            "bounds": [0.0, 0.5],
            "transform": "logit",
            "role": "label_param",
        },
        {
            "path": "electrodes.height_mm",
            "bounds": [0.2, 1.0],
            "transform": "identity",
            "role": "nuisance",
            "nominal": 0.6,
        },
    ],
}


def test_theta_spec_with_no_knobs_validates() -> None:
    """The Wave-1 case: SEP12 emits today's behavior, so the bank has a regime
    and nothing swept. An empty knob list is a statement — 'nothing varied' —
    so requiring at least one knob would make the migration unable to write a
    valid theta-spec at all."""
    _validator("GenerationParams").validate(WAVE1_THETA_SPEC)


def test_theta_spec_with_knobs_validates() -> None:
    _validator("GenerationParams").validate(SWEEP_THETA_SPEC)


def test_theta_spec_requires_both_halves() -> None:
    """A knob list without a regime is uninterpretable — a recovered region only
    means something inside the structure it was recovered in."""
    validator = _validator("GenerationParams")
    for missing in ("regime", "knobs"):
        doc = {k: v for k, v in SWEEP_THETA_SPEC.items() if k != missing}
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(doc)


def test_tuned_param_path_is_deliberately_unconstrained() -> None:
    """CL-024 deferred the path grammar and its resolver out of v0.6.0, so any
    non-empty string is legal here. This test exists to make that deferral
    visible: if someone later adds a pattern, they should be changing this test
    on purpose rather than discovering it broke a producer."""
    defs = get_schema(_SCHEMA_NAME)["$defs"]
    path_schema = defs["TunedParam"]["properties"]["path"]
    assert "pattern" not in path_schema and "enum" not in path_schema
    validator = _validator("TunedParam")
    for path in ("substrate.density", "cell_model.params.g_CaL_scale", "mixer.snr_db", "x"):
        validator.validate({"path": path, "bounds": [0.0, 1.0]})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"path": "", "bounds": [0.0, 1.0]})


def test_tuned_param_bounds_are_a_pair() -> None:
    """One number isn't a range and three is a design the emulator can't read."""
    validator = _validator("TunedParam")
    for bad in ([0.5], [0.0, 0.5, 1.0], []):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({"path": "substrate.density", "bounds": bad})


@pytest.mark.parametrize("field", ["transform", "role"])
def test_tuned_param_rejects_an_unknown_vocabulary_value(field: str) -> None:
    """transform and role are closed vocabularies: a typo'd 'nuisence' would
    otherwise silently reclassify a confound as the signal being measured."""
    knob = {"path": "substrate.density", "bounds": [0.0, 0.5], field: "made_up"}
    with pytest.raises(jsonschema.ValidationError):
        _validator("TunedParam").validate(knob)


def test_tuned_param_nominal_is_optional() -> None:
    """A knob that is always swept has no pinned value to record."""
    _validator("TunedParam").validate({"path": "backend.params.diffusion", "bounds": [0.1, 2.0]})


def test_theta_spec_does_not_store_knob_values() -> None:
    """The theta-spec says WHICH knobs vary and over what range; the values a
    given simulation used live in its per-function config, reachable by `path`.
    Storing values here too would be a second source of truth for the same
    number — the flaw the whole restructure exists to remove."""
    props = get_schema(_SCHEMA_NAME)["$defs"]["TunedParam"]["properties"]
    assert "value" not in props and "values" not in props
    assert set(props) == {"path", "bounds", "transform", "role", "nominal"}
