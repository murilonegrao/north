"""CIP 2020 codes (NCES Classification of Instructional Programs) and North's scope families.

Scope (record 0002, R1, R2): 11.xx computing, 30.70 data science, 30.71 data analytics,
52.12 information systems (flagged, never STEM OPT).
"""

from __future__ import annotations

import re

CIP6_RE = re.compile(r"^\d{2}\.\d{4}$")

# Family key -> code prefix (with the dot). Order is the display order.
FAMILIES: dict[str, str] = {"11": "11.", "30.70": "30.70", "30.71": "30.71", "52.12": "52.12"}


def is_cip6(code: str) -> bool:
    return bool(CIP6_RE.match(code))


def normalize_cip(raw: str) -> str:
    """Return the ``NN.NNNN`` form of a 6-digit CIP ("110701", "11.0701", "1.0101" -> ...)."""
    s = raw.strip().strip('="')
    if "." in s:
        head, tail = s.split(".", 1)
        s = head.zfill(2) + "." + tail.ljust(4, "0")
    elif s.isdigit() and len(s) in (5, 6):
        s = s.zfill(6)
        s = s[:2] + "." + s[2:]
    if not is_cip6(s):
        raise ValueError(f"not a 6-digit CIP code: {raw!r}")
    return s


def cip_family(code: str) -> str | None:
    """Scope family of a 6-digit CIP code, or None when the code is out of scope."""
    for family, prefix in FAMILIES.items():
        if code.startswith(prefix):
            return family
    return None
