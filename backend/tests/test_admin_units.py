"""Admin pieces that need no database: TOTP, password policy, upload recognition, schedules."""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path

import pytest

from north.auth import totp
from north.auth.passwords import WeakPassword, check_policy, hash_password, verify_password
from north.ingest.us.jobs import _validate_sync, _validate_upload, destination
from north.jobs.registry import next_weekday_at

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # base32 of "12345678901234567890"


def test_totp_rfc6238_vectors() -> None:
    # RFC 6238 appendix B (SHA-1), last 6 of the 8 digits.
    assert totp.code_at(RFC_SECRET, 59 // 30) == "287082"
    assert totp.code_at(RFC_SECRET, 1111111109 // 30) == "081804"
    assert totp.code_at(RFC_SECRET, 20000000000 // 30) == "353130"


def test_totp_window_and_replay() -> None:
    now = 1_000_000_000.0
    step = totp.current_step(now)
    code = totp.code_at(RFC_SECRET, step)
    assert totp.verify(RFC_SECRET, code, now=now) == step
    assert totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, step - 1), now=now) == step - 1
    assert totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, step - 2), now=now) is None
    assert totp.verify(RFC_SECRET, code, now=now, last_step=step) is None  # replay
    assert totp.verify(RFC_SECRET, "12345", now=now) is None
    assert totp.verify(RFC_SECRET, "abcdef", now=now) is None


def test_totp_provisioning() -> None:
    s = totp.new_secret()
    assert len(s) == 32 and s.isalnum()
    uri = totp.provisioning_uri(s, "ana", "North admin")
    assert uri.startswith("otpauth://totp/North%20admin%3Aana?secret=")
    assert totp.qr_svg_data_uri(uri).startswith("data:image/svg+xml")


def test_password_policy_and_hash() -> None:
    for bad in ("short", "a" * 20, "x" * 300, "ana-is-the-best-admin"):
        with pytest.raises(WeakPassword):
            check_policy(bad, username="ana")
    check_policy("correct horse battery staple", username="ana")
    h = hash_password("correct horse battery staple")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "correct horse battery staple") == (True, False)
    assert verify_password(h, "wrong")[0] is False
    assert verify_password(None, "anything")[0] is False


def _zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return path


def test_upload_destination(tmp_path: Path) -> None:
    z = _zip(tmp_path / "x.zip", {"a.csv": b"x"})
    assert destination("HD2024.zip", b"PK\x03\x04", z, "stemList2024.pdf") == (
        "ipeds", "ipeds/HD2024.zip")
    assert destination("C2024_A_Dict.zip", b"PK", z, "stemList2024.pdf")[0] == "ipeds"
    assert destination("certified-school-list-11-18-26.pdf", b"%PDF-1.7", z,
                       "stemList2024.pdf") == ("sevp", "sevp/certified-school-list-11-18-26.pdf")
    assert destination("stemList2024.pdf", b"%PDF", z, "stemList2024.pdf")[0] == "dhs"
    assert destination("FY27_FMRs.xlsx", b"PK", z, "stemList2024.pdf")[0] == "hud"
    dapip = _zip(tmp_path / "d.zip", {"x/InstitutionCampus.csv": b"a",
                                     "x/AccreditationRecords.csv": b"b"})
    assert destination("whatever.zip", b"PK", dapip, "stemList2024.pdf") == (
        "dapip", "dapip/extracted")
    with pytest.raises(ValueError, match="must be a zip"):
        destination("HD2024.zip", b"%PDF", z, "stemList2024.pdf")
    with pytest.raises(ValueError, match="not recognised"):
        destination("notes.txt", b"hello", z, "stemList2024.pdf")
    with pytest.raises(ValueError, match="not recognised"):
        destination("other.zip", b"PK", z, "stemList2024.pdf")


def test_job_param_validation() -> None:
    assert _validate_sync({}) == {"states": "ALL", "fetch": True}
    assert _validate_sync({"states": "tx,nm", "fetch": False}) == {"states": "TX,NM",
                                                                  "fetch": False}
    with pytest.raises(ValueError):
        _validate_sync({"states": "XX"})
    good = {"file": "0" * 32 + "__HD2024.zip", "sha256": "a" * 64}
    assert _validate_upload(good)["file"] == good["file"]
    for bad in ({**good, "file": "../../etc/passwd"}, {**good, "file": "0" * 32 + "__../x"},
                {**good, "sha256": "zz"}):
        with pytest.raises(ValueError):
            _validate_upload(bad)


def test_next_weekday_at() -> None:
    first = next_weekday_at(0, 6)
    sunday = dt.datetime(2026, 11, 22, 4, 0, tzinfo=dt.UTC)
    assert first(sunday) == dt.datetime(2026, 11, 23, 6, 0, tzinfo=dt.UTC)
    monday_late = dt.datetime(2026, 11, 23, 7, 0, tzinfo=dt.UTC)
    assert first(monday_late) == dt.datetime(2026, 11, 30, 6, 0, tzinfo=dt.UTC)
