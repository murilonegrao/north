import pytest

from north.domain.countries.us.cip import cip_family, is_cip6, normalize_cip
from north.domain.countries.us.stem import (
    FLAG_NO_STEM_OPT_EXTENSION,
    StemRule,
    program_flags,
    stem_opt_eligibility,
)
from north.domain.verified import SourceKind, Status, is_curated, verified

RULE = StemRule.build("2024-07-22", ["11.0701", "30.7001", "30.7101"],
                      {"whole_series": ["14", "26", "27", "40"]})


def test_listed_code_is_confirmed_eligible() -> None:
    r = stem_opt_eligibility("11.0701", RULE)
    assert (r.eligible, r.status, r.rule_version) == (True, Status.CONFIRMED_OFFICIAL,
                                                      "2024-07-22")


def test_whole_series_makes_unlisted_codes_eligible() -> None:
    # Record 0002/A14: a code added to series 14 after the list was printed is still STEM.
    assert stem_opt_eligibility("14.9999", RULE).eligible is True
    assert stem_opt_eligibility("27.0599", RULE).status == Status.CONFIRMED_OFFICIAL


def test_unlisted_code_is_confirmed_negative() -> None:
    # R12: a confirmed "no" on a yes/no field is confirmed_negative + false.
    r = stem_opt_eligibility("52.1201", RULE)
    assert (r.eligible, r.status) == (False, Status.CONFIRMED_NEGATIVE)


def test_without_rule_or_valid_code_the_answer_is_unknown() -> None:
    assert stem_opt_eligibility("11.0701", None).status == Status.UNKNOWN
    assert stem_opt_eligibility("11.0701", None).eligible is None
    assert stem_opt_eligibility("11.07", RULE).status == Status.UNKNOWN


def test_claim_mismatch_only_when_claimed_and_not_eligible() -> None:
    assert stem_opt_eligibility("52.1201", RULE, claimed_by_program=True).claim_mismatch
    assert not stem_opt_eligibility("52.1201", RULE, claimed_by_program=None).claim_mismatch
    assert not stem_opt_eligibility("11.0701", RULE, claimed_by_program=True).claim_mismatch


@pytest.mark.parametrize(("cip", "flags"), [
    ("52.1201", [FLAG_NO_STEM_OPT_EXTENSION]), ("52.1299", [FLAG_NO_STEM_OPT_EXTENSION]),
    ("52.1301", []), ("11.0701", []),
])
def test_52_12_flag(cip: str, flags: list[str]) -> None:
    assert program_flags(cip) == flags


@pytest.mark.parametrize(("cip", "family"), [
    ("11.0701", "11"), ("11.9999", "11"), ("30.7001", "30.70"), ("30.7104", "30.71"),
    ("52.1206", "52.12"), ("52.1301", None), ("30.0101", None), ("14.0901", None),
])
def test_cip_family(cip: str, family: str | None) -> None:
    assert cip_family(cip) == family


def test_normalize_cip() -> None:
    assert normalize_cip("110701") == "11.0701"
    assert normalize_cip("1.0101") == "01.0101"
    assert normalize_cip(" 30.7001 ") == "30.7001"
    assert is_cip6("11.0701") and not is_cip6("99")
    with pytest.raises(ValueError):
        normalize_cip("99")


def test_verified_value_rules() -> None:
    v = verified(1, Status.CONFIRMED_OFFICIAL, source_kind=SourceKind.UPLOADED_FILE,
                 source_url="https://example.invalid", verified_at="2026-11-21")
    assert v["status"] == "confirmed_official" and not is_curated(v)
    with pytest.raises(ValueError):
        verified(1, Status.CONFIRMED_OFFICIAL)  # no source
    with pytest.raises(ValueError):
        verified(1, Status.UNKNOWN)  # unknown has no value
    with pytest.raises(ValueError):
        verified(1, Status.EXTRACTED_UNVERIFIED, source_url="https://x.invalid")
    page = verified(1, Status.REPORTED_BY_PROGRAM, source_kind=SourceKind.PAGE,
                    source_url="https://x.invalid", verified_at="2026-11-21")
    assert is_curated(page)
