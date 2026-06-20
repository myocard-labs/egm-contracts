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
from .egm_class_model_metadata import validate_egm_class_model_metadata
from .hybrid_eval_metrics import validate_hybrid_eval_metrics
from .iafdb_bank import validate_iafdb_bank
from .noise_bank import validate_noise_bank
from .noise_bank_run_record import validate_noise_bank_run_record
from .synthetic_bank import validate_synthetic_bank
from .training_metrics import validate_training_metrics
from .training_run_record import validate_training_run_record

__all__ = [
    "ValidationResult",
    "validate_egm_class_model_metadata",
    "validate_hybrid_eval_metrics",
    "validate_iafdb_bank",
    "validate_noise_bank",
    "validate_noise_bank_run_record",
    "validate_synthetic_bank",
    "validate_training_metrics",
    "validate_training_run_record",
]
