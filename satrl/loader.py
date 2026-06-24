"""Load a client JSON spec, run normalisation/de-duplication, and produce a
:class:`ClientData` ready for the builder plus the merge diagnostics for the memo.

Expected JSON shape::

    {
      "particulars": {"name": ..., "pan": ..., "status": ..., "gender": ...,
                       "assessment_year": ..., "previous_year": ..., "address": ...},
      "profile":     {"has_business": false, "presumptive_44ad": false, ...},
      "sources": {
        "ais":           {"bank_accounts": [...], "investments": [...]},
        "balance_sheet": {"bank_accounts": [...], "investments": [...]},
        "computation":   {"bank_accounts": [...], "investments": [...]}
      },
      "excluded_notes": ["Loan from X — excluded per firm convention", ...]
    }
"""

from __future__ import annotations

import json
from typing import Tuple

from .model import ClientData, Particulars, Profile, VALID_SOURCES
from .normalize import MergeDiagnostics, merge_bank_accounts, merge_investments


def _per_source(sources: dict, field: str) -> dict:
    return {src: (sources.get(src, {}) or {}).get(field, []) for src in VALID_SOURCES}


def load_client(spec: dict) -> Tuple[ClientData, MergeDiagnostics, MergeDiagnostics]:
    particulars = Particulars(**spec.get("particulars", {}))
    profile = Profile(**spec.get("profile", {}))
    sources = spec.get("sources", {})

    banks, bank_diag = merge_bank_accounts(_per_source(sources, "bank_accounts"))
    invs, inv_diag = merge_investments(_per_source(sources, "investments"))

    client = ClientData(
        particulars=particulars, profile=profile,
        bank_accounts=banks, investments=invs,
        excluded_notes=spec.get("excluded_notes", []),
    )
    return client, bank_diag, inv_diag


def load_client_file(path: str):
    with open(path, encoding="utf-8") as fh:
        return load_client(json.load(fh))
