"""Command-line entry point.

    python -m satrl.cli client.json [--outdir DIR]

Writes ``Requirement_<ClientName>_FY_<years>.xlsx`` and a matching
``..._memo.txt`` next to it (or in ``--outdir``).
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from .builder import build_requirement_xlsx
from .loader import load_client_file
from .memo import build_reconciliation_memo


def _slug(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip())


def _fy_token(previous_year: str) -> str:
    # "2025-26 (...)" -> "202526"
    m = re.match(r"\s*(\d{4})-(\d{2})", previous_year or "")
    return f"{m.group(1)}{m.group(2)}" if m else "FY"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate a SAT ITR Requirement List.")
    ap.add_argument("client_json", help="path to the client spec JSON")
    ap.add_argument("--outdir", default=".", help="output directory (default: cwd)")
    args = ap.parse_args(argv)

    client, bank_diag, inv_diag = load_client_file(args.client_json)
    os.makedirs(args.outdir, exist_ok=True)

    base = f"Requirement_{_slug(client.particulars.name)}_FY_{_fy_token(client.particulars.previous_year)}"
    xlsx_path = os.path.join(args.outdir, base + ".xlsx")
    memo_path = os.path.join(args.outdir, base + "_memo.txt")

    decision = build_requirement_xlsx(client, xlsx_path)
    memo = build_reconciliation_memo(client, bank_diag, inv_diag, decision)
    with open(memo_path, "w", encoding="utf-8") as fh:
        fh.write(memo)

    print(f"Wrote {xlsx_path}")
    print(f"Wrote {memo_path}")
    print(f"Form: {decision.form}  |  Due: {decision.due_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
