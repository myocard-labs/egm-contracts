"""Artifact role classification: hand-written logic over the generated vocabulary.

The :class:`Role` enum and the id-prefix to role table (:data:`ROLE_PREFIXES`) are
GENERATED - single-sourced in ``codegen/roles.json`` and emitted to
``_generated/python/roles.py`` (and, eventually, to the C++ side the same way).
This module adds the one piece that is logic, not data: :func:`role_of`, which
maps a stable artifact id to its :class:`Role` by prefix. It is hand-written per
language; the vocabulary it reads is not.
"""

from __future__ import annotations

from myocard_egm_contracts._generated.python.roles import ROLE_PREFIXES, Role

__all__ = ["ROLE_PREFIXES", "Role", "role_of"]

# Longest prefix first so a longer prefix is never shadowed by a shorter one it
# contains (defensive - the current vocabulary has no such overlap).
_PREFIXES_LONGEST_FIRST = sorted(ROLE_PREFIXES, key=len, reverse=True)


def role_of(artifact_id: str) -> Role:
    """The :class:`Role` a stable artifact id encodes, by its prefix.

    Raises ``ValueError`` if the id carries no known role prefix - an unrecognized
    prefix is a data bug, not a silent "other" bucket.
    """
    for prefix in _PREFIXES_LONGEST_FIRST:
        if artifact_id.startswith(prefix):
            return ROLE_PREFIXES[prefix]
    raise ValueError(f"artifact id has no known role prefix: {artifact_id!r}")
