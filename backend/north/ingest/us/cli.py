"""Command line for US ingestion. Run from backend/ (or in the image, from /app):

    # Download every official file into a raw directory, then load the whole country:
    uv run python -m north.ingest.us.cli sync --raw <dir> --state ALL

    # Only download (nothing touches the database):
    uv run python -m north.ingest.us.cli fetch --raw <dir>

    # Load files already on disk (downloaded, uploaded or copied by hand):
    uv run python -m north.ingest.us.cli load-all --state TX --ipeds-dir <dir> \\
        --sevp-pdf <pdf> --dapip-dir <dir> [--dhs-csv <csv>] [--dhs-pdf <pdf>]

    # Counts per state and the source files in use, to compare two databases:
    uv run python -m north.ingest.us.cli report > report.json

--state takes one USPS code, a comma-separated list (TX,NM,OK) or ALL (every state, DC and
territory). Steps run in the order of UML 5.1 (R3): reference, IPEDS per state, DHS STEM once,
then SEVP and DAPIP per state. Each step prints a JSON summary; a file already ingested for the
same scope is skipped (idempotent on source + sha256), so a sync with nothing new is cheap.

Exit codes: 0 done; 1 a step failed or a required file is missing; 3 loaded, but a source
needs a person (blocked, failed download, or a changed DHS STEM PDF).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from north.ingest.us import dapip, dhs_stem, ipeds, reference, sevp
from north.ingest.us.common import StepResult
from north.ingest.us.eligibility import recompute_stem_eligibilities
from north.ingest.us.fetch import fetch_all, inputs_from_raw
from north.ingest.us.report import report
from north.ingest.us.states import STATE_NAMES
from north.repository.db import get_sessionmaker

HERE = Path(__file__).resolve()
EXIT_ATTENTION = 3


def reference_dir() -> Path:
    """data/reference: NORTH_REFERENCE_DIR, the source tree, or the image (/app/data)."""
    env = os.environ.get("NORTH_REFERENCE_DIR")
    if env:
        return Path(env)
    for candidate in (HERE.parents[4] / "data" / "reference",   # <repo>/backend/north/...
                      HERE.parents[3] / "data" / "reference"):  # /app/north/...
        if candidate.is_dir():
            return candidate
    return HERE.parents[4] / "data" / "reference"


def default_isced() -> Path:
    return reference_dir() / "cip-isced-f.csv"


def default_dhs_csv() -> Path:
    """Newest dhs-stem-list-YYYY-MM-DD.csv (ISO dates sort as text)."""
    found = sorted(reference_dir().glob("dhs-stem-list-*.csv"))
    if not found:
        raise FileNotFoundError(f"no dhs-stem-list-*.csv in {reference_dir()}")
    return found[-1]


def parse_states(raw: str) -> list[str]:
    """"TX" -> ["TX"]; "tx, nm" -> ["NM", "TX"]; "ALL" -> every known code, sorted."""
    raw = raw.strip().upper()
    if raw == "ALL":
        return sorted(STATE_NAMES)
    codes = sorted({c.strip() for c in raw.split(",") if c.strip()})
    unknown = [c for c in codes if c not in STATE_NAMES]
    if unknown or not codes:
        raise argparse.ArgumentTypeError(f"unknown state code(s): {', '.join(unknown) or raw!r}")
    return codes


class Printer:
    """One indented JSON block per step for a single state, one line per step otherwise."""

    def __init__(self, compact: bool, emit: Callable[[str], None] | None = None) -> None:
        self.compact = compact
        self.emit = emit or (lambda line: print(line, flush=True))
        self.ok = True
        self.totals: Counter[str] = Counter()

    def __call__(self, result: StepResult | dict[str, Any], state: str | None = None) -> bool:
        data = result.as_dict() if isinstance(result, StepResult) else dict(result)
        if state:
            data["state"] = state
        self.totals[f"{data.get('source')}:{data.get('status', 'done')}"] += 1
        self.emit(json.dumps(data, sort_keys=True, indent=None if self.compact else 2))
        ok = data.get("status") != "failed"
        self.ok &= ok
        return ok


def load_all(s: Session, states: Iterable[str], *, ipeds_dir: Path, dhs_csv: Path,
             dhs_meta: Path | None, dhs_pdf: Path | None, sevp_file: Path, dapip_path: Path,
             isced_csv: Path, emit: Callable[[str], None] | None = None) -> bool:
    states = list(states)
    out = Printer(compact=len(states) > 1, emit=emit)
    out({"source": "reference_cip_isced", **reference.load_cip_isced(s, isced_csv)})
    for st in states:
        for r in ipeds.ingest_ipeds_dir(s, ipeds_dir, st):
            out(r, st)
    out(dhs_stem.ingest_dhs_stem(s, dhs_csv, dhs_meta, dhs_pdf))
    for st in states:
        out(sevp.ingest_sevp(s, sevp_file, st), st)
        out(dapip.ingest_dapip(s, dapip_path, st), st)
    if len(states) > 1:
        out.emit(json.dumps({"summary": dict(sorted(out.totals.items())), "states": len(states)}))
    return out.ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="north.ingest.us.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name: str, help_: str, state: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        if state:
            p.add_argument("--state", type=parse_states, default=["TX"],
                           help="USPS code, comma-separated codes, or ALL (default TX)")
        return p

    p = cmd("fetch", "download every official file into --raw (no database)", state=False)
    p.add_argument("--raw", type=Path, required=True)
    p = cmd("sync", "fetch into --raw, then load-all from the files found there")
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--no-fetch", action="store_true", help="load what is already in --raw")

    p = cmd("load-all", "every source, in order")
    p.add_argument("--ipeds-dir", type=Path, required=True)
    p.add_argument("--dhs-csv", type=Path, help="default: newest in data/reference")
    p.add_argument("--dhs-meta", type=Path)
    p.add_argument("--dhs-pdf", type=Path,
                   help="official PDF; its sha256 must equal the meta file_sha256")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--sevp-pdf", type=Path)
    g.add_argument("--sevp-csv", type=Path, help="CSV derived from the PDF by the spike parser")
    p.add_argument("--dapip-dir", type=Path, required=True, help="directory or the DAPIP zip")
    p.add_argument("--isced-csv", type=Path)

    cmd("report", "counts per state and source files in use, as JSON", state=False)
    p = cmd("reference", "CIP -> ISCED-F map from data/reference", state=False)
    p.add_argument("--isced-csv", type=Path)
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
    p.add_argument("--csv", type=Path)
    p.add_argument("--meta", type=Path)
    p.add_argument("--pdf", type=Path, help="official PDF; its sha256 must equal file_sha256")
    p = cmd("sevp", "SEVP certified school list (PDF or derived CSV)")
    p.add_argument("--file", type=Path, required=True)
    p = cmd("dapip", "DAPIP export (zip or extracted directory)")
    p.add_argument("--path", type=Path, required=True)
    cmd("recompute-eligibilities", "recompute us.stem_opt for every program", state=False)

    a = ap.parse_args(argv)

    if a.cmd == "fetch":
        results = fetch_all(a.raw, dhs_stem.default_meta_path(default_dhs_csv()))
        bad = [r for r in results if not r.ok]
        print(json.dumps({"fetched": len(results), "needs_attention": len(bad)}), flush=True)
        return EXIT_ATTENTION if bad else 0

    attention = False
    if a.cmd == "sync":
        dhs_csv = default_dhs_csv()
        meta = dhs_stem.default_meta_path(dhs_csv)
        if not a.no_fetch:
            results = fetch_all(a.raw, meta)
            attention = any(not r.ok for r in results)
        try:
            inp = inputs_from_raw(a.raw, meta)
        except FileNotFoundError as e:
            print(json.dumps({"status": "failed", "error": str(e)}), flush=True)
            return 1

    states: list[str] = getattr(a, "state", [])
    with get_sessionmaker()() as s:
        if a.cmd == "sync":
            ok = load_all(s, states, ipeds_dir=inp.ipeds_dir, dhs_csv=dhs_csv, dhs_meta=meta,
                          dhs_pdf=inp.dhs_pdf, sevp_file=inp.sevp_pdf, dapip_path=inp.dapip_dir,
                          isced_csv=default_isced())
            if not ok:
                return 1
            return EXIT_ATTENTION if attention else 0
        if a.cmd == "load-all":
            ok = load_all(s, states, ipeds_dir=a.ipeds_dir, dhs_csv=a.dhs_csv or default_dhs_csv(),
                          dhs_meta=a.dhs_meta, dhs_pdf=a.dhs_pdf,
                          sevp_file=a.sevp_pdf or a.sevp_csv, dapip_path=a.dapip_dir,
                          isced_csv=a.isced_csv or default_isced())
            return 0 if ok else 1
        if a.cmd == "report":
            print(json.dumps(report(s), indent=2, sort_keys=True, default=str), flush=True)
            return 0
        out = Printer(compact=len(states) > 1)
        if a.cmd == "reference":
            out({"source": "reference_cip_isced",
                 **reference.load_cip_isced(s, a.isced_csv or default_isced())})
        elif a.cmd == "dhs-stem":
            out(dhs_stem.ingest_dhs_stem(s, a.csv or default_dhs_csv(), a.meta, a.pdf))
        elif a.cmd == "recompute-eligibilities":
            n = recompute_stem_eligibilities(s, author="ingest:recompute")
            s.commit()
            out({"source": "recompute", "programs": n})
        for st in states:
            if a.cmd == "ipeds":
                for r in ipeds.ingest_ipeds_dir(s, a.dir, st):
                    out(r, st)
            elif a.cmd == "ipeds-hd":
                out(ipeds.ingest_hd(s, a.file, st), st)
            elif a.cmd == "ipeds-c-a":
                out(ipeds.ingest_c_a(s, a.file, st, a.dict), st)
            elif a.cmd == "ipeds-ic-ay":
                out(ipeds.ingest_ic_ay(s, a.file, st), st)
            elif a.cmd == "sevp":
                out(sevp.ingest_sevp(s, a.file, st), st)
            elif a.cmd == "dapip":
                out(dapip.ingest_dapip(s, a.path, st), st)
    return 0 if out.ok else 1


if __name__ == "__main__":
    sys.exit(main())
