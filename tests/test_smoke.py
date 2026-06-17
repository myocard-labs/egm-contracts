"""Smoke test — confirms the package imports and __version__ is sane.

Keep this test alive for the life of the package; it's the canary for
broken installs and bad packaging metadata.
"""

from __future__ import annotations

import re

import myocard_egm_contracts


def test_package_imports() -> None:
    assert myocard_egm_contracts is not None


def test_version_is_pep440() -> None:
    # Loose PEP 440 check — accepts X.Y.Z, X.Y.Z.devN, X.Y.ZrcN, etc.
    assert re.match(r"^\d+\.\d+\.\d+", myocard_egm_contracts.__version__), (
        f"non-PEP440 version: {myocard_egm_contracts.__version__!r}"
    )


def test_generated_models_are_present() -> None:
    """All six schema modules should be importable after codegen runs."""
    expected = [
        "hybrid_eval_metrics",
        "iafdb_bank",
        "metrics",
        "model_metadata",
        "run_record",
        "synthetic_bank",
    ]
    for name in expected:
        mod = getattr(myocard_egm_contracts, name)
        assert mod is not None, (
            f"Missing generated module {name!r}. "
            "Run `python codegen/gen_python.py` from the repo root."
        )
