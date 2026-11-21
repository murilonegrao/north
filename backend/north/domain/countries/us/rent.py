"""Rent benchmark helpers for HUD Fair Market Rents (decision record 0002, R6)."""

from __future__ import annotations

import math

MAX_BEDROOMS = 4  # HUD FMR publishes 0 to 4 bedrooms


def bedrooms_for(dependents: int) -> int:
    """Bedrooms used to pick the HUD FMR value: ceil((1 + dependents) / 2), at most 4.

    The student plus their dependents share rooms two by two. A family of 5
    (student + 4 dependents) needs 3 bedrooms.
    """
    if dependents < 0:
        raise ValueError("dependents must be zero or more")
    return min(math.ceil((1 + dependents) / 2), MAX_BEDROOMS)
