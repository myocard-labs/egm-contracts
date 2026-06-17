"""File-level conformance checkers for every schema.

Each ``validate_*`` function takes a path to a file on disk, opens it,
maps its contents onto the schema-shaped envelope (HDF5 attrs → dict;
CSV row → dict; JSON → as-is), and runs ``jsonschema`` validation
against the corresponding ``.schema.json``. Returns a
:class:`ValidationResult` whose ``ok`` field is True iff the file
conforms.

The validators contain the only HDF5↔JSON-Schema mapping logic in the
package. The schemas stay declarative; the mapping (e.g., the
JSON-encoded sub-config attrs on the synthetic bank, the cross-field
``window_samples`` check on the IAFDB bank) lives here.

Example::

    from pathlib import Path
    from myocard_egm_contracts.validators import validate_iafdb_bank

    result = validate_iafdb_bank(Path("iafdb_v1.h5"))
    if not result:
        for issue in result.issues:
            print(issue)
"""

from __future__ import annotations

from ._result import ValidationResult
from .hybrid_eval_metrics import validate_hybrid_eval_metrics
from .iafdb_bank import validate_iafdb_bank
from .metrics import validate_metrics
from .model_metadata import validate_model_metadata
from .run_record import validate_run_record
from .synthetic_bank import validate_synthetic_bank

__all__ = [
    "ValidationResult",
    "validate_hybrid_eval_metrics",
    "validate_iafdb_bank",
    "validate_metrics",
    "validate_model_metadata",
    "validate_run_record",
    "validate_synthetic_bank",
]
