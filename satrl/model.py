"""Data model for the SAT ITR Requirement List generator.

A client is described by three things:
  * ``particulars`` — assessee identity, pulled from the computation of income;
  * ``profile``     — the few facts needed to decide ITR form & due date;
  * ``sources``     — the raw bank/investment items extracted from each of the
                      three source documents (balance sheet, AIS, computation).

The generator does the normalisation, de-duplication, form determination and
reconciliation itself, so the input only needs to be a faithful transcription
of what each source document shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# The three source documents an item can appear in.
SOURCE_AIS = "ais"
SOURCE_BALANCE_SHEET = "balance_sheet"
SOURCE_COMPUTATION = "computation"
VALID_SOURCES = (SOURCE_AIS, SOURCE_BALANCE_SHEET, SOURCE_COMPUTATION)


@dataclass
class Particulars:
    name: str
    pan: str
    status: str = "Individual"          # "Individual" or "HUF"
    gender: str = ""                    # "male" / "female" — picks Sir / Madam
    assessment_year: str = ""           # e.g. "2026-27"
    previous_year: str = ""             # e.g. "2025-26 (01.04.2025 to 31.03.2026)"
    address: str = ""


@dataclass
class Profile:
    """Facts that decide the ITR form and statutory due date."""
    has_business: bool = False          # any business / professional income
    presumptive_44ad: bool = False      # presumptive business u/s 44AD
    presumptive_44ada: bool = False     # presumptive profession u/s 44ADA
    has_capital_gains: bool = False
    tax_audit_44ab: bool = False        # audit applicable u/s 44AB
    gst_turnover: Optional[float] = None
    section_10_26: bool = False         # Manipur tribal exemption — note only
    notes: str = ""                     # free-text the memo will echo


@dataclass
class BankAccount:
    bank: str
    account_no: str = ""
    account_type: str = ""              # "Savings", "Current", ...
    branch: str = ""
    sources: List[str] = field(default_factory=list)


@dataclass
class Investment:
    """An investment row.

    Provide either a ready-made ``label`` (used verbatim in column B) or a
    structured ``kind`` that the formatter turns into a label.  ``kind`` values
    understood by :mod:`satrl.builder`:
        fixed_deposit, recurring_deposit, kvp, nsc, bond, share, mutual_fund,
        lic, gold, demat.
    """
    label: str = ""
    ref: str = "—"
    kind: str = ""
    # structured fields used by the label formatter
    entity: str = ""                    # bank / AMC / issuer
    rta: str = ""                       # "CAMS" or "KFintech" for mutual funds
    branch: str = ""
    sources: List[str] = field(default_factory=list)
    matured: bool = False               # excluded from list, noted in memo
    category: str = "investment"        # for exclusion handling


@dataclass
class ClientData:
    particulars: Particulars
    profile: Profile = field(default_factory=Profile)
    bank_accounts: List[BankAccount] = field(default_factory=list)
    investments: List[Investment] = field(default_factory=list)
    # Items deliberately omitted per firm convention (loans, property, fixed
    # assets) — captured only so the memo can record the reason.
    excluded_notes: List[str] = field(default_factory=list)
