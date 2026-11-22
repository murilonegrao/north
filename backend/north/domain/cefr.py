"""CEFR bands used by language courses and the placement estimate (record 0008/T13, T23).

``A0`` is the band below A1 ("pre-A1"): the Irish lists write it for courses open to complete
beginners, so it is kept as written instead of being folded into A1.
"""

from __future__ import annotations

BANDS: tuple[str, ...] = ("A0", "A1", "A2", "B1", "B2", "C1", "C2")
_RANK = {b: n for n, b in enumerate(BANDS)}


def is_band(value: object) -> bool:
    return isinstance(value, str) and value in _RANK


def rank(band: str) -> int:
    """Position of a band (A0 = 0 ... C2 = 6); ValueError for anything else."""
    try:
        return _RANK[band]
    except KeyError:
        raise ValueError(f"not a CEFR band: {band!r}") from None


def bands_up_to(band: str) -> tuple[str, ...]:
    """Every band at or below ``band``: the entry levels a learner at ``band`` can join."""
    return BANDS[: rank(band) + 1]
