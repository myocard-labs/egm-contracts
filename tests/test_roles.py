"""Tests for the artifact-role vocabulary + role_of (myocard_egm_contracts.roles).

The Role enum + ROLE_PREFIXES are generated from codegen/roles.json; role_of is
hand-written. These check the classification logic and guard the vocabulary
against drifting from its source and from the id patterns in common.schema.json.
"""

from __future__ import annotations

import json
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
