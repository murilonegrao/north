"""Limits for zip archives from uploads (FR-26): refuse zip bombs before decompressing.

Official files are far below these limits (C2024_A.csv: 63 MB at 13:1; xlsx parts under 1 MB
at under 20:1). ``zipfile`` stops reading at the declared ``file_size`` and checks the CRC, so
a member cannot inflate past the size checked here.
"""

from __future__ import annotations

import zipfile

MAX_MEMBER_BYTES = 200 << 20
MAX_RATIO = 100


def check_member(z: zipfile.ZipFile, name: str,
                 max_bytes: int | None = None) -> zipfile.ZipInfo:
    """ZipInfo of ``name`` after checking its uncompressed size and compression ratio."""
    max_bytes = MAX_MEMBER_BYTES if max_bytes is None else max_bytes
    info = z.getinfo(name)
    if info.file_size > max_bytes:
        raise ValueError(f"{name}: {info.file_size} bytes uncompressed, over the {max_bytes} "
                         f"byte limit")
    if info.file_size and info.file_size > MAX_RATIO * max(info.compress_size, 1):
        raise ValueError(f"{name}: compression ratio over {MAX_RATIO}:1; refusing (zip bomb?)")
    return info


def read_member(z: zipfile.ZipFile, name: str, max_bytes: int | None = None) -> bytes:
    check_member(z, name, max_bytes)
    return z.read(name)
