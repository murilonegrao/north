"""Command line for US ingestion. Run from ``backend/``:

    uv run python -m north.ingest.us.cli load-all --state TX --ipeds-dir <dir> \\
        --dhs-csv <csv> [--dhs-pdf <pdf>] --sevp-pdf <pdf> --dapip-dir <dir>

Steps run in the order of UML 5.1 (R3). Each step prints a JSON summary; a file already
ingested for the same scope is skipped (idempotent on source + sha256).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from north.ingest.us import dapip, dhs_stem, ipeds, reference, sevp
from north.ingest.us.common import StepResult
from north.ingest.us.eligibility import recompute_stem_eligibilities
from north.repository.db import get_sessionmaker

REPO = Path(__file__).resolve().parents[4]
DEFAULT_ISCED = REPO / "data" / "reference" / "cip-isced-f.csv"


def _print(result: StepResult | dict[str, Any]) -> bool:
    data = result.as_dict() if isinstance(result, StepResult) else result
    print(json.dumps(data, indent=2, sort_keys=True), flush=True)
    return data.get("status") != "failed"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="north.ingest.us.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name: str, help_: str, state: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        if state:
            p.add_argument("--state", default="TX", help="USPS state code (default TX)")
        return p

    p = cmd("load-all", "every source, in order")
    p.add_argument("--ipeds-dir", type=Path, required=True)
    p.add_argument("--dhs-csv", type=Path, required=True)
    p.add_argument("--dhs-meta", type=Path)
    p.add_argument("--dhs-pdf", type=Path,
                   help="official PDF; its sha256 must equal the meta file_sha256")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--sevp-pdf", type=Path)
    g.add_argument("--sevp-csv", type=Path, help="CSV derived from the PDF by the spike parser")
    p.add_argument("--dapip-dir", type=Path, required=True, help="directory or the DAPIP zip")
    p.add_argument("--isced-csv", type=Path, default=DEFAULT_ISCED)

    p = cmd("reference", "CIP -> ISCED-F map from data/reference", state=False)
    p.add_argument("--isced-csv", type=Path, default=DEFAULT_ISCED)
    p = cmd("ipeds", "HD, C_A and IC_AY from one directory")
    p.add_argument("--dir", type=Path, required=True)
    p = cmd("ipeds-hd", "IPEDS HD<year> directory file")
    p.add_argument("--file", type=Path, required=True)
    p = cmd("ipeds-c-a", "IPEDS C<year>_A completions file")
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--dict", type=Path, help="C<year>_A_Dict.zip (CIP titles, AWLEVEL check)")
    p = cmd("ipeds-ic-ay", "IPEDS IC<year>_AY charges file")
    p.add_argument("--file", type=Path, required=True)
    p = cmd("dhs-stem", "DHS STEM list CSV + meta json", state=False)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--meta", type=Path)
    p.add_argument("--pdf", type=Path, help="official PDF; its sha256 must equal file_sha256")
    p = cmd("sevp", "SEVP certified school list (PDF or derived CSV)")
    p.add_argument("--file", type=Path, required=True)
    p = cmd("dapip", "DAPIP export (zip or extracted directory)")
    p.add_argument("--path", type=Path, required=True)
    cmd("recompute-eligibilities", "recompute us.stem_opt for every program", state=False)

    a = ap.parse_args(argv)
    ok = True
    with get_sessionmaker()() as s:
        if a.cmd == "load-all":
            ok = _print({"source": "reference_cip_isced",
                         **reference.load_cip_isced(s, a.isced_csv)})
            for r in ipeds.ingest_ipeds_dir(s, a.ipeds_dir, a.state):
                ok &= _print(r)
            ok &= _print(dhs_stem.ingest_dhs_stem(s, a.dhs_csv, a.dhs_meta, a.dhs_pdf))
            ok &= _print(sevp.ingest_sevp(s, a.sevp_pdf or a.sevp_csv, a.state))
            ok &= _print(dapip.ingest_dapip(s, a.dapip_dir, a.state))
            return 0 if ok else 1
        if a.cmd == "reference":
            ok = _print({"source": "reference_cip_isced", **reference.load_cip_isced(
                s, a.isced_csv)})
        elif a.cmd == "ipeds":
            for r in ipeds.ingest_ipeds_dir(s, a.dir, a.state):
                ok &= _print(r)
        elif a.cmd == "ipeds-hd":
            ok = _print(ipeds.ingest_hd(s, a.file, a.state))
        elif a.cmd == "ipeds-c-a":
            ok = _print(ipeds.ingest_c_a(s, a.file, a.state, a.dict))
        elif a.cmd == "ipeds-ic-ay":
            ok = _print(ipeds.ingest_ic_ay(s, a.file, a.state))
        elif a.cmd == "dhs-stem":
            ok = _print(dhs_stem.ingest_dhs_stem(s, a.csv, a.meta, a.pdf))
        elif a.cmd == "sevp":
            ok = _print(sevp.ingest_sevp(s, a.file, a.state))
        elif a.cmd == "dapip":
            ok = _print(dapip.ingest_dapip(s, a.path, a.state))
        elif a.cmd == "recompute-eligibilities":
            n = recompute_stem_eligibilities(s, author="ingest:recompute")
            s.commit()
            ok = _print({"source": "recompute", "programs": n})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
