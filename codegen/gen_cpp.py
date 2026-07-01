"""Generate C++ header structs from the JSON Schema files in schemas/.

STUB — not yet implemented. Wires up when the C++ deployment chat lands.

Plan (recorded in the ``feedback-schemas-json-schema-first`` memory):

- Tool: ``quicktype`` (https://quicktype.io) or
  ``nlohmann/json-schema-codegen``. Pick when the C++ work begins; both are
  viable and the choice mostly affects code style, not correctness.
- Output: one .hpp per .schema.json into
  ``src/myocard_egm_contracts/_generated/cpp/``, plus a top-level
  ``myocard_egm_contracts.hpp`` umbrella header.
- Role vocabulary: ``codegen/roles.json`` (the single source the Python side
  emits to ``_generated/python/roles.py``) must also be emitted here -- a C++
  ``Role`` enum + an id-prefix -> Role lookup -- so the vocabulary stays
  single-sourced across languages. The ``role_of()`` logic over it is
  hand-written per language, not generated.
- Consumption: C++ projects pull egm-contracts via CMake ``FetchContent_Declare``
  pinned to a release tag, then ``#include
  <myocard_egm_contracts/synthetic_bank.hpp>``.
- Header-only — no separate compiled library. egm-contracts does not ship a
  built C++ artifact; downstream projects compile the generated headers into
  their own build.
- CI: when the script is implemented, the ``codegen-drift`` job in
  ``.github/workflows/ci.yml`` should re-run it and assert clean diff (same
  pattern as ``gen_python.py``).

Run from the repo root::

    python codegen/gen_cpp.py
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "gen_cpp.py is a documented stub. The C++ deployment chat will fill it in;\n"
        "see the docstring above for the planned approach.",
        file=sys.stderr,
    )
    raise NotImplementedError(
        "C++ codegen not yet implemented. "
        "See feedback-schemas-json-schema-first memory for context."
    )


if __name__ == "__main__":
    raise SystemExit(main())
