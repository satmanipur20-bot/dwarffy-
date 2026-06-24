"""Normalisation, merge-mapping and de-duplication rules (system prompt §2).

The merge functions are deliberately diagnostic: besides the de-duplicated
list they hand back the facts the reconciliation memo needs — which items
appeared in only one source, which had genuine digit mismatches, and which
were matured/closed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .model import BankAccount, Investment, VALID_SOURCES


# Merged / renamed banks → surviving entity (system prompt §2).
BANK_MERGE_MAP = {
    "united bank of india": "Punjab National Bank",
    "allahabad bank": "Indian Bank",
    "vijaya bank": "Bank of Baroda",
    "dena bank": "Bank of Baroda",
}

# Defunct banks needing a "where did the funds move?" confirmation.
DEFUNCT_BANKS = {"paytm payments bank"}


def normalize_bank_name(name: str) -> str:
    """Apply the merged/renamed-bank map; otherwise return the name trimmed."""
    if not name:
        return ""
    cleaned = re.sub(r"\s+", " ", name).strip()
    return BANK_MERGE_MAP.get(cleaned.lower(), cleaned)


def is_defunct_bank(name: str) -> bool:
    return re.sub(r"\s+", " ", (name or "")).strip().lower() in DEFUNCT_BANKS


def account_key(account_no: str) -> str:
    """De-duplication key for an account number.

    Account numbers are TEXT and leading zeros are preserved for *display*, but
    two numbers that differ only in zero-padding are the SAME account, so the
    key strips leading zeros and any separators.
    """
    digits = re.sub(r"[^0-9A-Za-z]", "", account_no or "")
    stripped = digits.lstrip("0")
    return stripped if stripped else digits  # all-zero / empty edge case


def canonical_display(variants: List[str]) -> str:
    """Pick the display form among padding variants: the longest (most padded)
    non-empty string, matching how the firm's templates present them."""
    real = [v for v in variants if v and v.strip() and v.strip() != "—"]
    if not real:
        return "—"
    return max(real, key=len)


@dataclass
class MergeDiagnostics:
    single_source: List[str]          # appears in only one source
    digit_mismatch: List[str]         # genuine mismatch after padding normalised
    matured: List[str]                # matured/closed instruments (excluded)
    defunct: List[str]                # Paytm-style defunct-bank flags


def _bank_dedup_key(acc_bank: str, branch: str, acct_type: str, acct_no: str) -> Tuple:
    # Distinct branches of the same number are kept separate (the firm lists
    # branch-specific accounts individually), so branch is part of the key.
    return (
        normalize_bank_name(acc_bank).lower(),
        (branch or "").strip().lower(),
        (acct_type or "").strip().lower(),
        account_key(acct_no),
    )


def merge_bank_accounts(
    per_source: Dict[str, List[dict]]
) -> Tuple[List[BankAccount], MergeDiagnostics]:
    """Collect every bank account from every source, de-duplicate and diagnose."""
    grouped: Dict[Tuple, dict] = {}
    for src, items in per_source.items():
        if src not in VALID_SOURCES:
            raise ValueError(f"unknown source {src!r}")
        for raw in items:
            bank = normalize_bank_name(raw.get("bank", ""))
            branch = raw.get("branch", "")
            atype = raw.get("account_type", "")
            ano = raw.get("account_no", "")
            key = _bank_dedup_key(bank, branch, atype, ano)
            slot = grouped.setdefault(
                key, {"bank": bank, "branch": branch, "account_type": atype,
                      "numbers": [], "sources": set()}
            )
            slot["numbers"].append(ano)
            slot["sources"].add(src)

    accounts: List[BankAccount] = []
    single, mismatch, defunct = [], [], []
    for slot in grouped.values():
        display_no = canonical_display(slot["numbers"])
        acc = BankAccount(
            bank=slot["bank"], account_no=display_no,
            account_type=slot["account_type"], branch=slot["branch"],
            sources=sorted(slot["sources"]),
        )
        accounts.append(acc)

        label = f"{acc.bank} {acc.account_type}".strip() + (f" ({acc.branch})" if acc.branch else "")
        if len(acc.sources) == 1:
            single.append(f"{label} — A/c {display_no}: appears only in {acc.sources[0]}")
        # genuine mismatch: same key but distinct non-empty digit strings remain
        distinct = {account_key(n) for n in slot["numbers"] if account_key(n)}
        raw_distinct = {re.sub(r'[^0-9A-Za-z]', '', n) for n in slot["numbers"] if n}
        if len({n.lstrip('0') for n in raw_distinct}) > 1:
            mismatch.append(f"{label}: differing numbers across sources {sorted(raw_distinct)}")
        if is_defunct_bank(acc.bank) or is_defunct_bank(slot["bank"]):
            defunct.append(f"{label} — A/c {display_no}: bank is defunct; confirm where funds moved")

    # Order is preserved as first-seen across sources (the firm's data order),
    # not forced alphabetical.
    return accounts, MergeDiagnostics(single, mismatch, [], defunct)


def merge_investments(
    per_source: Dict[str, List[dict]]
) -> Tuple[List[Investment], MergeDiagnostics]:
    """De-duplicate investments; split out matured/closed (excluded from list)."""
    grouped: Dict[Tuple, dict] = {}
    for src, items in per_source.items():
        if src not in VALID_SOURCES:
            raise ValueError(f"unknown source {src!r}")
        for raw in items:
            kind = (raw.get("kind") or "").strip().lower()
            entity = normalize_bank_name(raw.get("entity", "")) if raw.get("entity") else ""
            ref = raw.get("ref", "—")
            label = raw.get("label", "")
            key = (kind, entity.lower(), label.lower(), account_key(ref))
            slot = grouped.setdefault(key, {"raw": dict(raw), "entity": entity,
                                            "refs": [], "sources": set()})
            slot["refs"].append(ref)
            slot["sources"].add(src)

    live: List[Investment] = []
    single, matured = [], []
    for slot in grouped.values():
        raw = slot["raw"]
        inv = Investment(
            label=raw.get("label", ""), ref=canonical_display(slot["refs"]),
            kind=(raw.get("kind") or "").strip().lower(), entity=slot["entity"],
            rta=raw.get("rta", ""), branch=raw.get("branch", ""),
            sources=sorted(slot["sources"]),
            matured=bool(raw.get("matured", False)),
            category=raw.get("category", "investment"),
        )
        name = inv.label or f"{inv.kind} {inv.entity}".strip()
        if inv.matured:
            matured.append(f"{name} — Ref {inv.ref}: matured/closed; excluded from list")
            continue
        if len(inv.sources) == 1:
            single.append(f"{name} — Ref {inv.ref}: appears only in {inv.sources[0]}")
        live.append(inv)

    return live, MergeDiagnostics(single, [], matured, [])
