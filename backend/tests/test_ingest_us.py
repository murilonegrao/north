"""Ingestion of the synthetic official files (needs NORTH_TEST_DATABASE_URL)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from north.ingest.us import ipeds
from north.ingest.us.sevp_pdf import date_from_filename
from north.repository.models import (
    Base,
    Campus,
    FieldChange,
    Institution,
    InstitutionContact,
    InstitutionIdentifier,
    Program,
    ProgramClassification,
    ProgramEligibility,
    ReconciliationTask,
    SourceFile,
)
from tests.conftest import FIXTURES, PLACEHOLDER, load_fixtures


def test_all_steps_succeed(loaded: dict) -> None:
    for name in ("ipeds_hd", "ipeds_c_a", "ipeds_ic_ay", "dhs_stem_list", "sevp_csl", "dapip"):
        assert loaded[name].status == "succeeded", (name, loaded[name].errors)


def test_hd_keeps_active_graduate_institutions_of_the_state(session: Session, loaded: dict) -> None:
    ids = set(session.scalars(select(Institution.id)))
    assert ids == {"900001", "900002", "900003"}  # not CA, not HLOFFER 3, not inactive
    i = session.get(Institution, "900001")
    assert (i.name, i.city, i.control, i.website) == (
        "Lone Star Test University", "Austin", "public", "https://www.lonestar-test.example/")
    assert session.get(Institution, "900003").control == "private_for_profit"
    idents = dict(session.execute(select(InstitutionIdentifier.scheme, InstitutionIdentifier.value)
                                  .where(InstitutionIdentifier.institution_id == "900001")).all())
    assert idents == {"unitid": "900001", "opeid": "09000100", "dapip": "100001"}
    campus = session.scalar(select(Campus).where(Campus.institution_id == "900001"))
    assert (campus.locality.scheme, campus.locality.code, campus.locality.name) == (
        "us_county_fips", "48453", "Travis County")


def test_c_a_programs_completions_and_classification(session: Session, loaded: dict) -> None:
    ids = set(session.scalars(select(Program.id)))
    # 14.0901 is out of scope, AWLEVEL 5 is not a master's, 99 is the total, CA is filtered.
    assert ids == {"900001-110701", "900001-521201", "900001-307101", "900002-110101",
                   "900002-307001", "900003-111003"}
    p = session.get(Program, "900001-110701")
    assert p.name == "Computer Science" and p.degree == "Master's"
    assert p.academic["title_source"] == "cip_title"
    c = p.academic["completions"]
    assert c["value"] == {"total": 12, "nonresident": 8, "year": "2023-24"}  # majors 1 + 2
    assert c["status"] == "confirmed_official" and c["source_kind"] == "uploaded_file"
    assert session.get(Program, "900001-307101").academic["completions"]["value"]["total"] == 0
    assert session.get(Program, "900001-521201").flags == ["no_stem_opt_extension"]
    pc = session.scalar(select(ProgramClassification).where(
        ProgramClassification.program_id == "900001-110701"))
    assert pc.is_primary and pc.verified["value"] == {"scheme": "cip2020", "code": "11.0701"}
    assert pc.classification.title == "Computer Science."


def test_ic_ay_tuition_is_institution_wide(session: Session, loaded: dict) -> None:
    t = session.get(Program, "900001-521201").cost["graduate_tuition_nonresident"]
    assert t["value"] == {"amount": 12000, "currency": "USD"}
    assert t["note_code"] == "institution_wide_average" and t["evidence"] == "IC2023_AY TUITION7"
    missing = session.get(Program, "900002-110101").cost["graduate_tuition_nonresident"]
    assert missing["status"] == "unknown" and missing["value"] is None


def test_stem_eligibilities(session: Session, loaded: dict) -> None:
    res = {pe.program_id: pe for pe in session.scalars(select(ProgramEligibility))}
    assert len(res) == 6
    assert res["900001-110701"].result["value"] is True
    assert res["900001-110701"].result["source_kind"] == "official_list"
    assert res["900001-521201"].result == {**res["900001-521201"].result, "value": False,
                                           "status": "confirmed_negative"}
    assert all(pe.rule_version == "2024-07-22" for pe in res.values())


def test_sevp_exact_match_and_reconciliation(session: Session, loaded: dict) -> None:
    def campus(unitid: str) -> Campus:
        return session.scalar(select(Campus).where(Campus.institution_id == unitid))

    a = campus("900001")
    assert a.sevp_campus_code == "DAL214F90000000"
    assert a.intl_authorization["value"] == {"scheme": "sevp", "authorized": True}
    assert a.intl_authorization["status"] == "confirmed_official"
    # The campus's own name wins over another campus of the same school in the same city.
    b = campus("900002")
    assert b.sevp_campus_code == "HOU214F90001000"
    assert b.intl_authorization["status"] == "confirmed_negative"  # F-1 N
    c = campus("900003")
    assert c.sevp_campus_code is None and c.intl_authorization["status"] == "unknown"
    tasks = session.scalars(select(ReconciliationTask).where(
        ReconciliationTask.kind == "sevp_match")).all()
    assert len(tasks) == 1 and tasks[0].candidates[0]["institution_id"] == "900003"
    # The school code is never stored as an identifier.
    assert not session.scalar(select(func.count()).select_from(InstitutionIdentifier).where(
        InstitutionIdentifier.value.like("%214F%")))


def test_dapip_accreditation(session: Session, loaded: dict) -> None:
    a = session.get(Institution, "900001").accreditation
    assert a["value"] == {"accreditor": "SACSCOC", "scheme": "us_ed_recognized",
                          "institutional": True}
    assert a["status"] == "confirmed_official" and "joined by unitid" in a["evidence"]
    b = session.get(Institution, "900002").accreditation  # preaccredited only
    assert b["status"] == "unknown"
    c = session.get(Institution, "900003").accreditation
    assert c["value"]["accreditor"] == "HLC" and "parent opeid" in c["evidence"]
    kinds = set(session.scalars(select(ReconciliationTask.kind)))
    assert "accreditation_review" in kinds


def test_contacts_land_only_in_the_private_table(session: Session, loaded: dict) -> None:
    """Record 0009: DAPIP administrators and the IPEDS HD chief administrator and general phone
    are kept privately; address, general phone and fax of DAPIP are never read."""
    for table in Base.metadata.sorted_tables:
        dump = session.execute(text(f"select coalesce(string_agg(t::text, ' '), '') "
                                    f"from {table.name} t")).scalar_one()
        assert PLACEHOLDER not in dump, table.name
        if table.name != "institution_contacts":
            for secret in ("Dapip Admin", "dapip.admin", "Chief Example", "0000000001"):
                assert secret not in dump, table.name
    rows = session.scalars(select(InstitutionContact).where(
        InstitutionContact.institution_id == "900001")).all()
    dapip = {(c.name, c.email, c.phone) for c in rows if c.source == "dapip"}
    # The institution's own row and its additional location (ParentDapipId 100001).
    assert ("Dapip Admin 1", "dapip.admin1@example.com", "+1 000 000 0001") in dapip
    assert ("Dapip Admin 4", "dapip.admin4@example.com", "+1 000 000 0004") in dapip
    hd = [(c.name, c.title, c.phone, c.email) for c in rows if c.source == "ipeds_hd"]
    assert hd == [("Chief Example 1", "President", "0000000001", None)]


def test_a_new_dapip_file_replaces_its_contacts(session: Session, loaded: dict,
                                                tmp_path: Path) -> None:
    from north.ingest.us import dapip

    d = tmp_path / "dapip-2026-12-01"
    shutil.copytree(FIXTURES / "dapip", d)
    campus = d / "InstitutionCampus.csv"
    campus.write_text(campus.read_text(encoding="utf-8").replace("Dapip Admin 1,", "New Admin,"),
                      encoding="utf-8")
    assert dapip.ingest_dapip(session, d, "TX").status == "succeeded"
    names = set(session.scalars(select(InstitutionContact.name).where(
        InstitutionContact.institution_id == "900001", InstitutionContact.source == "dapip")))
    assert "New Admin" in names and "Dapip Admin 1" not in names
    hd = session.scalars(select(InstitutionContact.name).where(
        InstitutionContact.source == "ipeds_hd", InstitutionContact.institution_id == "900001"))
    assert list(hd) == ["Chief Example 1"]  # other sources untouched


def test_field_changes_have_ingest_authors(session: Session, loaded: dict) -> None:
    authors = set(session.scalars(select(FieldChange.author)))
    assert {"ingest:ipeds_hd", "ingest:ipeds_c_a", "ingest:ipeds_ic_ay", "ingest:dhs_stem_list",
            "ingest:sevp_csl", "ingest:dapip"} <= authors
    paths = set(session.scalars(select(FieldChange.field_path).where(
        FieldChange.program_id == "900001-110701")))
    assert {"name", "academic.completions", "primary_classification",
            "cost.graduate_tuition_nonresident", "eligibility[us.stem_opt]"} <= paths


def test_rerun_is_idempotent(session: Session, ipeds_dir: Path, loaded: dict) -> None:
    changes = session.scalar(select(func.count()).select_from(FieldChange))
    again = load_fixtures(session, ipeds_dir)
    assert all(again[k].status == "skipped" for k in again if k != "reference")
    assert session.scalar(select(func.count()).select_from(SourceFile)) == 6
    assert session.scalar(select(func.count()).select_from(FieldChange)) == changes


def test_curated_value_is_not_overwritten(session: Session, ipeds_dir: Path,
                                          loaded: dict, tmp_path: Path) -> None:
    p = session.get(Program, "900001-110701")
    curated = {"value": {"total": 99, "nonresident": 1, "year": "2023-24"},
               "status": "reported_by_program", "source_kind": "page",
               "source_url": "https://lonestar-test.example/cs", "evidence": "x",
               "verified_at": "2026-11-20"}
    p.academic = {**p.academic, "completions": curated}
    session.commit()
    newer = tmp_path / "ipeds2"
    newer.mkdir()
    shutil.copy(ipeds_dir / "C2024_A_Dict.zip", newer / "C2025_A_Dict.zip")
    (newer / "C2025_A.csv").write_text(
        (ipeds_dir / "C2024_A.csv").read_text().replace("900001,11.0701,1,7,R,10", "900001,"
                                                        "11.0701,1,7,R,11"))
    r = ipeds.ingest_c_a(session, newer / "C2025_A.csv", "TX", newer / "C2025_A_Dict.zip")
    assert r.status == "succeeded"
    session.refresh(p)
    assert p.academic["completions"] == curated
    assert session.scalar(select(func.count()).select_from(ReconciliationTask).where(
        ReconciliationTask.kind == "value_conflict")) == 1


def test_failed_run_can_be_repeated(session: Session, tmp_path: Path) -> None:
    bad = tmp_path / "C2024_A.csv"
    bad.write_text("UNITID,CIPCODE,AWLEVEL\n900001,11.0701,7\n")
    d = tmp_path / "C2024_A_Dict.zip"
    from tests.conftest import DICT_ROWS, write_dictionary

    write_dictionary(d, [r if r[2] != "7" else [*r[:3], "Doctor's degree", *r[4:]]
                         for r in DICT_ROWS])
    assert ipeds.ingest_c_a(session, bad, "TX", d).status == "failed"
    write_dictionary(d, DICT_ROWS)
    assert ipeds.ingest_c_a(session, bad, "TX", d).status == "succeeded"


def test_sevp_date_from_filename() -> None:
    assert date_from_filename(Path("certified-school-list-11-18-26.pdf")) == "2026-11-18"
    assert date_from_filename(Path("sevp-certified-schools-2026-11-18.csv")) == "2026-11-18"


def _c_a(tmp_path: Path, ipeds_dir: Path, body: str) -> Path:
    d = tmp_path / "c_a"
    d.mkdir()
    shutil.copy(ipeds_dir / "C2024_A_Dict.zip", d / "C2025_A_Dict.zip")
    (d / "C2025_A.csv").write_text(body)
    return d


def test_c_a_missing_counts_are_unknown_not_zero(session: Session, ipeds_dir: Path,
                                                 loaded: dict, tmp_path: Path) -> None:
    # "." and an empty cell are "not reported", never 0 (BR-02); a known total stays known.
    d = _c_a(tmp_path, ipeds_dir,
             "UNITID,CIPCODE,MAJORNUM,AWLEVEL,CTOTALT,CNRALT\n"
             "900001,11.0701,1,7,10,.\n"      # nonresident unknown
             "900001,11.0701,2,7,2,1\n"
             "900001,52.1201,1,7,.,0\n"       # total unknown, known before -> kept + task
             "900002,11.0101,1,7,,\n"         # total unknown, known before -> kept + task
             "900003,11.0701,1,7,.,.\n")      # new program, total unknown
    r = ipeds.ingest_c_a(session, d / "C2025_A.csv", "TX", d / "C2025_A_Dict.zip")
    assert r.status == "succeeded", r.errors
    c = session.get(Program, "900001-110701").academic["completions"]
    assert c["value"] == {"total": 12, "nonresident": None, "year": "2024-25"}
    assert c["status"] == "confirmed_official" and "nonresident count unknown" in c["evidence"]
    new = session.get(Program, "900003-110701").academic["completions"]
    assert new["status"] == "unknown" and new["value"] is None
    kept = session.get(Program, "900001-521201").academic["completions"]
    assert kept["value"]["total"] == 3  # the 2024 value, not 0
    assert r.counts["programs_unknown_completions"] == 3
    assert r.counts["programs_unknown_nonresident"] == 1
    assert r.counts.get("programs_zero_completions", 0) == 0
    assert session.scalar(select(func.count()).select_from(ReconciliationTask).where(
        ReconciliationTask.kind == "value_missing")) == 2


def test_c_a_missing_column_is_unknown(session: Session, ipeds_dir: Path, loaded: dict,
                                       tmp_path: Path) -> None:
    d = _c_a(tmp_path, ipeds_dir, "UNITID,CIPCODE,MAJORNUM,AWLEVEL,CTOTALT\n"
                                  "900003,11.0701,1,7,4\n")
    r = ipeds.ingest_c_a(session, d / "C2025_A.csv", "TX", d / "C2025_A_Dict.zip")
    assert r.status == "succeeded", r.errors
    c = session.get(Program, "900003-110701").academic["completions"]
    assert c["value"] == {"total": 4, "nonresident": None, "year": "2024-25"}


def test_hd_plain_columns_logged_and_website_host_change_reviewed(
        session: Session, ipeds_dir: Path, loaded: dict, tmp_path: Path) -> None:
    hd = (ipeds_dir / "HD2024.csv").read_text(encoding="utf-8-sig")
    hd = (hd.replace("Lone Star Test University,", "Lone Star Test University System,")
            .replace("www.lonestar-test.example/", "www.lonestar-other.example/")
            .replace("https://gulf-test.example/", "https://www.gulf-test.example/admissions"))
    d = tmp_path / "hd"
    d.mkdir()
    (d / "HD2025.csv").write_text(hd)
    assert ipeds.ingest_hd(session, d / "HD2025.csv", "TX").status == "succeeded"
    i = session.get(Institution, "900001")
    assert (i.name, i.website) == ("Lone Star Test University System",
                                   "https://www.lonestar-other.example/")
    changes = {fc.field_path: (fc.old_value, fc.new_value) for fc in session.scalars(
        select(FieldChange).where(FieldChange.author == "ingest:ipeds_hd",
                                  FieldChange.field_path.like("institution[%")))
               if fc.old_value is not None}
    assert changes["institution[900001].name"] == ("Lone Star Test University",
                                                   "Lone Star Test University System")
    assert changes["institution[900001].website"][1] == "https://www.lonestar-other.example/"
    assert changes["institution[900002].website"][1] == "https://www.gulf-test.example/admissions"
    tasks = session.scalars(select(ReconciliationTask).where(
        ReconciliationTask.kind == "website_changed")).all()
    # Same host (www. and path aside) is routine; a new host is reviewed.
    assert [t.candidates[0]["institution_id"] for t in tasks] == ["900001"]


def test_sevp_only_explicit_n_is_negative(session: Session, loaded: dict, tmp_path: Path) -> None:
    from north.ingest.us import sevp

    src = (Path(__file__).parent / "fixtures" / "sevp" / "sevp-test-2026-11-18.csv").read_text()
    # 900002 is matched by its stored code; its F-1 cell is now blank.
    csv_path = tmp_path / "sevp-test-2026-11-25.csv"
    csv_path.write_text(src.replace("Gulf Coast Test College,N,Y,Houston",
                                    "Gulf Coast Test College,,Y,Houston"))
    campus = session.scalar(select(Campus).where(Campus.institution_id == "900002"))
    campus.intl_authorization = {"value": None, "status": "unknown"}
    session.commit()
    r = sevp.ingest_sevp(session, csv_path, "TX")
    assert r.status == "succeeded", r.errors
    session.refresh(campus)
    assert campus.intl_authorization["status"] == "unknown"
    assert r.counts["f1_flag_unknown"] == 1
    assert session.scalar(select(func.count()).select_from(ReconciliationTask).where(
        ReconciliationTask.kind == "sevp_flag")) == 1


def test_sevp_csv_rows_are_validated(session: Session, loaded: dict, tmp_path: Path) -> None:
    from north.ingest.us import sevp

    src = (Path(__file__).parent / "fixtures" / "sevp" / "sevp-test-2026-11-18.csv").read_text()
    bad = tmp_path / "sevp-test-2026-11-26.csv"
    bad.write_text(src.replace("HOU214F90001001", "DAL214F90000000"))  # duplicate code
    r = sevp.ingest_sevp(session, bad, "TX")
    assert r.status == "failed" and "duplicate" in r.errors[-1]


def test_dhs_digest_covers_meta(session: Session, loaded: dict, tmp_path: Path) -> None:
    from north.ingest.us import dhs_stem

    fx = Path(__file__).parent / "fixtures" / "dhs"
    shutil.copy(fx / "dhs-stem-list-test.csv", tmp_path / "dhs-stem-list-test.csv")
    shutil.copy(fx / "dhs-stem-list-test.meta.json", tmp_path / "dhs-stem-list-test.meta.json")
    meta = json.loads((fx / "dhs-stem-list-test.meta.json").read_text())
    csv_path = tmp_path / "dhs-stem-list-test.csv"
    assert dhs_stem.ingest_dhs_stem(session, csv_path).status == "skipped"  # same bytes
    meta["whole_series_included"] = ["14", "11"]
    (tmp_path / "dhs-stem-list-test.meta.json").write_text(json.dumps(meta))
    r = dhs_stem.ingest_dhs_stem(session, csv_path)
    assert r.status == "succeeded", r.errors
    from north.repository.models import EligibilityRule

    rule = session.scalar(select(EligibilityRule).where(EligibilityRule.version == "2024-07-22"))
    assert rule.params == {"whole_series": ["14", "11"]}


def test_dhs_refuses_pdf_with_other_sha(session: Session, tmp_path: Path) -> None:
    import pytest

    from north.ingest.us import dhs_stem

    fx = Path(__file__).parent / "fixtures" / "dhs"
    meta = json.loads((fx / "dhs-stem-list-test.meta.json").read_text())
    meta["file_sha256"] = "0" * 64
    meta_path = tmp_path / "m.meta.json"
    meta_path.write_text(json.dumps(meta))
    pdf = tmp_path / "stemList2024.pdf"
    pdf.write_bytes(b"%PDF-1.4 not the official file")
    with pytest.raises(ValueError, match="refusing"):
        dhs_stem.ingest_dhs_stem(session, fx / "dhs-stem-list-test.csv", meta_path, pdf)
    assert session.scalar(select(func.count()).select_from(SourceFile)) == 0
