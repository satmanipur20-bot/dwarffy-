"""SAT ITR Requirement List generator.

Turn a client's extracted bank/investment data into the firm's branded one-page
Requirement List (.xlsx) plus a reconciliation memo.
"""

from .builder import build_requirement_xlsx
from .forms import determine_form_and_due_date
from .loader import load_client, load_client_file
from .memo import build_reconciliation_memo
from .model import (BankAccount, ClientData, Investment, Particulars, Profile)

__all__ = [
    "build_requirement_xlsx", "determine_form_and_due_date",
    "load_client", "load_client_file", "build_reconciliation_memo",
    "BankAccount", "ClientData", "Investment", "Particulars", "Profile",
]
