"""Command line for the Irish lists. Run from backend/:

    uv run python -m north.ingest.ie.cli load --ilep <ILEP.xlsx> --trusted <TrustEd.xlsx>
    uv run python -m north.ingest.ie.cli report

Each list prints a JSON summary; a file already loaded is skipped (idempotent on sha256).
Exit code 1 when a step failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from north.ingest.ie.load import ingest_list
from north.ingest.report import report
from north.repository.db import get_sessionmaker


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="north.ingest.ie.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("load", help="load the ILEP and/or TrustEd files")
    p.add_argument("--ilep", type=Path)
    p.add_argument("--trusted", type=Path)
    p.add_argument("--exam-csv", type=Path, help="default: data/reference/ie_exam_names.csv")
    sub.add_parser("report", help="counts per county and source files in use, as JSON")
    a = ap.parse_args(argv)
    ok = True
    with get_sessionmaker()() as s:
        if a.cmd == "report":
            print(json.dumps(report(s, "IE"), indent=1, default=str))
            return 0
        for source, path in (("ie_ilep", a.ilep), ("ie_trusted", a.trusted)):
            if path is None:
                continue
            r = ingest_list(s, path, source, a.exam_csv)
            print(json.dumps(r.as_dict(), indent=1, default=str))
            ok = ok and r.status != "failed"
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
