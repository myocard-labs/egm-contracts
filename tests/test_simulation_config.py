"""Tests for simulation_config.schema.json — the per-function generation config.

These check the polymorphic machinery rather than the physics: that each
function's union discriminates on ``type``, that a variant's own constraints
bite, and that the shared definitions (Edge, PositionMm) are single-sourced.

The schema is a ``$defs`` library like ``common`` — no document validator, no
file written in this shape — so the tests validate values against a ``$ref``
into it, which is exactly how ``synthetic_bank`` consumes it.
"""

from __future__ import annotations

from typing import Any

import jsonschema
import pytest
from referencing import Registry, Resource

from myocard_egm_contracts.schema_info import get_schema

_SCHEMA_NAME = "simulation_config"

# One valid example per variant. Doubles as the shape SEP12 has to write in
# Wave 1 — if a producer can't satisfy these, the migration is wrong.
PATCH_2D: dict[str, Any] = {"type": "patch_2d", "size_mm": 40.0, "dr_mm": 0.25}
COURTEMANCHE: dict[str, Any] = {"type": "courtemanche", "params": {"g_CaL_scale": 0.8}}
ALIEV_PANFILOV: dict[str, Any] = {"type": "aliev_panfilov", "ap_time_unit_ms": 12.9}
UNIFORM_FIBROSIS: dict[str, Any] = {"type": "uniform_random_fibrosis", "density": 0.3}
PLANAR_EDGE: dict[str, Any] = {"type": "planar_edge", "edges": ["top"], "voltage": 1.0}
POINT: dict[str, Any] = {"type": "point", "position_mm": [20.0, 20.0]}
S1S2: dict[str, Any] = {
    "type": "s1s2",
    "site": {"type": "planar_edge", "edges": ["left"], "voltage": 1.0},
    "s1_interval_ms": 400.0,
    "s2_interval_ms": 250.0,
}
ELECTRODES: dict[str, Any] = {
    "type": "centered_grid_2d",
    "n_rows": 5,
    "n_cols": 5,
    "spacing_mm": 2.0,
    "height_mm": 0.6,
    "pairs": [
        {
            "pair_index": 0,
            "electrode_indices": [0, 1],
            "electrode_row": 0,
            "height_mm": 0.6,
            "midpoint_mm": [17.0, 16.0],
        }
    ],
}
FINITEWAVE: dict[str, Any] = {"type": "finitewave", "output_fs_hz": 1000.0}
GLOBAL_LABEL: dict[str, Any] = {"type": "global_density", "thresholds": [0.1]}
LOCAL_LABEL: dict[str, Any] = {"type": "local_density", "thresholds": [0.1], "radius_mm": 2.0}


def _validator(def_name: str) -> jsonschema.Draft202012Validator:
    """Build a validator for one ``$def``, the way synthetic_bank references it."""
    schema = get_schema(_SCHEMA_NAME)
    registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return jsonschema.Draft202012Validator(
        {"$ref": f"{schema['$id']}#/$defs/{def_name}"}, registry=registry
    )


# ---------------------------------------------------------------------------
# Each function's union accepts its variants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("function", "value"),
    [
        ("Geometry", PATCH_2D),
        ("CellModel", COURTEMANCHE),
        ("CellModel", ALIEV_PANFILOV),
        ("Substrate", UNIFORM_FIBROSIS),
        ("Activation", PLANAR_EDGE),
        ("Activation", POINT),
        ("Activation", S1S2),
        ("Electrodes", ELECTRODES),
        ("Backend", FINITEWAVE),
        ("LabelPolicy", GLOBAL_LABEL),
        ("LabelPolicy", LOCAL_LABEL),
    ],
)
def test_variant_validates_against_its_function(function: str, value: dict[str, Any]) -> None:
    _validator(function).validate(value)


@pytest.mark.parametrize(
    ("function", "value"),
    [
        ("Geometry", COURTEMANCHE),  # right shape, wrong function
        ("Substrate", PLANAR_EDGE),
        ("LabelPolicy", FINITEWAVE),
        ("Activation", {"type": "spiral_reentry", "position_mm": [1.0, 2.0]}),  # unknown variant
    ],
)
def test_wrong_variant_is_rejected(function: str, value: dict[str, Any]) -> None:
    """The discriminator is load-bearing: a config object that wandered into the
    wrong column has to fail here, because every one of these is stored as an
    opaque JSON string in its own HDF5 column and nothing else would catch it."""
    with pytest.raises(jsonschema.ValidationError):
        _validator(function).validate(value)


def test_missing_discriminator_is_rejected() -> None:
    """Without `type` there is no way to know which variant was intended, so a
    permissive read here would silently pick one."""
    with pytest.raises(jsonschema.ValidationError):
        _validator("Substrate").validate({"density": 0.3})


# ---------------------------------------------------------------------------
# Variant-level constraints
# ---------------------------------------------------------------------------


def test_fibrosis_density_bounds_are_the_physical_ones() -> None:
    """density is a fraction: 0 (exactly healthy) is legal, 1 is not — a fully
    fibrotic patch cannot propagate, so it is a producer bug, not a sample."""
    validator = _validator("Substrate")
    validator.validate({"type": "uniform_random_fibrosis", "density": 0.0})
    for bad in (1.0, 1.5, -0.1):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({"type": "uniform_random_fibrosis", "density": bad})


def test_planar_edge_requires_at_least_one_edge_and_rejects_duplicates() -> None:
    """An empty edge list is a stimulus that never fires; a repeated edge is a
    config-generation bug that would otherwise silently stimulate twice."""
    validator = _validator("Activation")
    validator.validate({"type": "planar_edge", "edges": ["top", "bottom"]})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"type": "planar_edge", "edges": []})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"type": "planar_edge", "edges": ["top", "top"]})


def test_planar_edge_rejects_an_unknown_edge_name() -> None:
    with pytest.raises(jsonschema.ValidationError):
        _validator("Activation").validate({"type": "planar_edge", "edges": ["diagonal"]})


def test_grid_needs_two_columns_to_form_a_bipolar_pair() -> None:
    """n_cols >= 2 is the producer's own invariant (specs.CenteredGrid2D raises
    on it); encoding it here catches a bad config before a simulation runs."""
    bad = {**ELECTRODES, "n_cols": 1}
    with pytest.raises(jsonschema.ValidationError):
        _validator("Electrodes").validate(bad)


def test_position_is_two_or_three_dimensional() -> None:
    """Coordinates follow the active geometry — 2D patch or 3D mesh. A 1- or
    4-element position means the producer and the geometry disagree."""
    validator = _validator("Activation")
    validator.validate({"type": "point", "position_mm": [1.0, 2.0, 3.0]})
    for bad in ([1.0], [1.0, 2.0, 3.0, 4.0]):
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({"type": "point", "position_mm": bad})


def test_label_policy_scales_from_binary_to_multiclass() -> None:
    """One threshold is the binary healthy/fibrotic policy; several give the
    Phase-2 severity bands. The point of the array is that multiclass needs no
    new variant and no contracts bump — only a longer list and a longer
    LabelNames map."""
    validator = _validator("LabelPolicy")
    validator.validate({"type": "global_density", "thresholds": [0.1]})
    validator.validate({"type": "global_density", "thresholds": [0.05, 0.2, 0.4]})


def test_label_policy_needs_at_least_one_threshold() -> None:
    """Zero thresholds is one class, i.e. a policy that labels nothing — a
    config bug rather than a degenerate-but-valid case."""
    with pytest.raises(jsonschema.ValidationError):
        _validator("LabelPolicy").validate({"type": "global_density", "thresholds": []})


def test_label_policies_do_not_name_their_classes() -> None:
    """Class names live in LabelNames only. Carrying healthy_name/fibrotic_name
    on the policy as well meant two places to state the same thing — and they
    could disagree, with nothing to catch it."""
    defs = get_schema(_SCHEMA_NAME)["$defs"]
    for policy in ("GlobalDensityLabel", "LocalDensityLabel"):
        props = defs[policy]["properties"]
        assert "healthy_name" not in props and "fibrotic_name" not in props, (
            f"{policy} names its classes; LabelNames owns that"
        )


def test_s1s2_nests_a_real_activation_not_a_parallel_site_type() -> None:
    """The protocol reuses the single-shot variants rather than duplicating
    their fields into 'site' objects that would have to be kept identical."""
    defs = get_schema(_SCHEMA_NAME)["$defs"]
    for gone in ("ActivationSite", "EdgeStripSite", "PointSite"):
        assert gone not in defs, f"{gone} is back — the duplication returned"
    assert defs["S1S2Activation"]["properties"]["site"]["$ref"] == "#/$defs/SingleShotActivation"
    _validator("Activation").validate(
        {
            "type": "s1s2",
            "site": {"type": "point", "position_mm": [20.0, 20.0]},
            "s1_interval_ms": 400.0,
            "s2_interval_ms": 250.0,
        }
    )


def test_a_protocol_cannot_nest_another_protocol() -> None:
    """SingleShotActivation excludes protocol variants, which is what keeps the
    nesting one level deep instead of arbitrarily recursive."""
    with pytest.raises(jsonschema.ValidationError):
        _validator("Activation").validate(
            {
                "type": "s1s2",
                "site": {
                    "type": "s1s2",
                    "site": {"type": "point", "position_mm": [1.0, 2.0]},
                    "s1_interval_ms": 400.0,
                    "s2_interval_ms": 250.0,
                },
                "s1_interval_ms": 400.0,
                "s2_interval_ms": 250.0,
            }
        )


def test_label_names_keys_are_stringified_ints() -> None:
    """JSON object keys are strings, so the int label map round-trips as
    {"0": ...}; a non-numeric key means something other than a label leaked in."""
    validator = _validator("LabelNames")
    validator.validate({"0": "healthy", "1": "fibrotic"})
    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"healthy": "0"})


# ---------------------------------------------------------------------------
# Single-sourcing — the same drift guard the ID patterns carry
# ---------------------------------------------------------------------------


def _collect_inline(node: Any, out: list[str], *, key_name: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == key_name and isinstance(value, list):
                out.append(repr(value))
            else:
                _collect_inline(value, out, key_name=key_name)
    elif isinstance(node, list):
        for item in node:
            _collect_inline(item, out, key_name=key_name)


def test_edge_vocabulary_is_defined_once() -> None:
    """Every variant naming an edge $refs the shared Edge def. Two inline copies
    is how a single-shot stimulus and a paced protocol end up disagreeing about
    what "top" means — the failure would only surface as a wrong-looking
    wavefront in a figure."""
    defs = get_schema(_SCHEMA_NAME)["$defs"]
    assert defs["Edge"]["enum"] == ["top", "bottom", "left", "right"]
    inline: list[str] = []
    for name, subschema in defs.items():
        if name != "Edge":
            _collect_inline(subschema, inline, key_name="enum")
    assert "['top', 'bottom', 'left', 'right']" not in inline, (
        f"an edge enum is inlined instead of $ref'ing Edge: {inline}"
    )


def test_coordinate_arrays_are_defined_once() -> None:
    """position_mm / midpoint_mm / positions_mm items all $ref PositionMm, so
    the 2-or-3-dimensional rule can't drift between them."""
    defs = get_schema(_SCHEMA_NAME)["$defs"]
    assert defs["PositionMm"]["minItems"] == 2
    assert defs["PositionMm"]["maxItems"] == 3
    for owner, prop in (
        ("PointActivation", "position_mm"),
        ("BipolarPair", "midpoint_mm"),
    ):
        assert defs[owner]["properties"][prop]["$ref"] == "#/$defs/PositionMm", (
            f"{owner}.{prop} does not $ref PositionMm"
        )


def test_every_function_union_carries_a_discriminator() -> None:
    """The `discriminator` annotation is what makes codegen emit a tagged union
    rather than a bare anyOf, so a consumer gets the concrete variant type back
    instead of having to sniff `type` itself."""
    defs = get_schema(_SCHEMA_NAME)["$defs"]
    unions = [name for name, sub in defs.items() if "oneOf" in sub]
    assert unions, "no polymorphic functions found — the schema shape changed"
    for name in unions:
        assert defs[name].get("discriminator", {}).get("propertyName") == "type", (
            f"{name} is a union without a type discriminator"
        )
