"""Tests for the artifact-role vocabulary + role_of (myocard_egm_contracts.roles).

The Role enum + ROLE_PREFIXES are generated from codegen/roles.json; role_of is
hand-written. These check the classification logic and guard the vocabulary
against drifting from its source and from the id patterns in common.schema.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from myocard_egm_contracts import ROLE_PREFIXES, Role, role_of

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ROLES_JSON = _REPO_ROOT / "codegen" / "roles.json"
_COMMON_SCHEMA = _REPO_ROOT / "src" / "myocard_egm_contracts" / "schemas" / "common.schema.json"


def test_role_of_classifies_every_prefix() -> None:
    assert role_of("tbank_synthetic_v1_2026-06-25") is Role.training_bank
    assert role_of("ptbank_pretrain_2026-06-20") is Role.pretraining_bank
    assert role_of("lpred_synth_val_2026-06-25") is Role.labeled_prediction_bank
    assert role_of("upred_iafdb_2026-06-25") is Role.unlabeled_prediction_bank
    assert role_of("nbank_iafdb_2026-06-15") is Role.noise_bank
    assert role_of("run_v1_2026-06-25") is Role.training_run
    assert role_of("model_egm_classifier_2026-06-25") is Role.model
    assert role_of("obs_saturation_2026-06-26") is Role.observation
    assert role_of("fig_feature_distributions") is Role.figure
    assert role_of("paper_phase_1_5_realism") is Role.paper


def test_role_of_rejects_unknown_prefix() -> None:
    with pytest.raises(ValueError, match="no known role prefix"):
        role_of("widget_foo_2026-01-01")


def test_role_prefixes_bijective_with_role() -> None:
    assert len(ROLE_PREFIXES) == len(Role)
    assert set(ROLE_PREFIXES.values()) == set(Role)


def test_generated_matches_roles_json_source() -> None:
    source = json.loads(_ROLES_JSON.read_text(encoding="utf-8"))["roles"]
    assert {r["prefix"]: r["name"] for r in source} == {
        prefix: role.value for prefix, role in ROLE_PREFIXES.items()
    }


def test_prefixes_documented_in_common_schema() -> None:
    """Drift guard: every role prefix is documented in common.schema.json."""
    text = _COMMON_SCHEMA.read_text(encoding="utf-8")
    for prefix in ROLE_PREFIXES:
        assert prefix in text, f"prefix {prefix!r} missing from common.schema.json"


# ---------------------------------------------------------------------------
# ArtifactId role-prefix validation (B16) — the pattern enforces the vocabulary
# ---------------------------------------------------------------------------

# fig_ / paper_ are roles but NOT ArtifactId prefixes: figures and papers carry
# FigureId / PaperId, which have their own patterns. Excluded deliberately.
_NON_ARTIFACT_PREFIXES = frozenset({"fig_", "paper_"})


def _artifact_id_pattern() -> str:
    pattern: str = json.loads(_COMMON_SCHEMA.read_text(encoding="utf-8"))["$defs"]["ArtifactId"][
        "pattern"
    ]
    return pattern


def _artifact_id_alternation() -> set[str]:
    """The prefix alternation the ArtifactId pattern actually enforces."""
    pattern = _artifact_id_pattern()
    match = re.match(r"\^\(([a-z|]+)\)_", pattern)
    assert match is not None, f"ArtifactId pattern is not a prefix alternation: {pattern}"
    return {f"{alt}_" for alt in match.group(1).split("|")}


def test_artifact_id_alternation_matches_roles_json() -> None:
    """The pattern's prefixes ARE the role vocabulary, minus fig_/paper_.

    This is what keeps the hand-written schema single-sourced against
    codegen/roles.json without making the schema a codegen output: add a role
    there and forget the pattern here, and this fails.
    """
    expected = {r["prefix"] for r in json.loads(_ROLES_JSON.read_text(encoding="utf-8"))["roles"]}
    assert _artifact_id_alternation() == expected - _NON_ARTIFACT_PREFIXES


@pytest.mark.parametrize("prefix", sorted(set(ROLE_PREFIXES) - _NON_ARTIFACT_PREFIXES))
def test_artifact_id_pattern_accepts_every_artifact_role(prefix: str) -> None:
    pattern = _artifact_id_pattern()
    assert re.match(pattern, f"{prefix}example_name_2026-07-30")
    assert re.match(pattern, f"{prefix}example_name"), "dateless ids stay legal (v0.5.3)"


@pytest.mark.parametrize(
    "bad_id",
    [
        "widget_foo_2026-01-01",  # not a role at all
        "bank_synthetic_v1",  # plausible-looking near-miss
        "fig_feature_distributions",  # a real role, but a FigureId not an ArtifactId
        "paper_phase_1_5_realism",  # ditto, PaperId
        "tbank",  # prefix with no name
        "TBANK_upper_case",
    ],
)
def test_artifact_id_pattern_rejects_non_roles(bad_id: str) -> None:
    """Before B16 the pattern took any ``[a-z]+_`` prefix, so a typo'd or
    invented role sailed through and only surfaced downstream as an
    unclassifiable artifact."""
    assert re.match(_artifact_id_pattern(), bad_id) is None


def test_every_accepted_prefix_is_classifiable_by_role_of() -> None:
    """The two halves agree: anything the schema accepts, role_of can name."""
    for prefix in _artifact_id_alternation():
        assert role_of(f"{prefix}example_2026-07-30") is ROLE_PREFIXES[prefix]
