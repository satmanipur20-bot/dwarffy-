"""Reconciliation memo (system prompt §5).

Never silently accept a discrepancy: this memo flags single-source items,
genuine digit mismatches, matured/closed instruments, deliberate omissions,
and records the concluded form & due date with reasoning.
"""

from __future__ import annotations

from typing import List

from .forms import FormDecision
from .model import ClientData
from .normalize import MergeDiagnostics


def build_reconciliation_memo(client: ClientData, bank_diag: MergeDiagnostics,
                              inv_diag: MergeDiagnostics,
                              decision: FormDecision) -> str:
    p = client.particulars
    lines: List[str] = []
    lines.append("RECONCILIATION MEMO")
    lines.append(f"Client: {p.name}  |  PAN: {p.pan}  |  A.Y. {p.assessment_year}")
    lines.append("=" * 72)

    def section(title, items, empty="None."):
        lines.append("")
        lines.append(title)
        if items:
            lines.extend(f"  - {it}" for it in items)
        else:
            lines.append(f"  {empty}")

    section("(a) Appearing in only ONE source — confirm whether to include:",
            bank_diag.single_source + inv_diag.single_source)

    section("(b) Genuine digit / format mismatches (after normalising zero-padding):",
            bank_diag.digit_mismatch + inv_diag.digit_mismatch)

    section("(c) Matured / closed instruments excluded from the list:",
            inv_diag.matured + bank_diag.matured)

    defunct = bank_diag.defunct + inv_diag.defunct
    if defunct:
        section("(b') Defunct-bank balances — confirm where funds moved:", defunct)

    section("(d) Items deliberately omitted per firm convention:",
            client.excluded_notes,
            empty="None recorded. (Loans & advances, immovable property and "
                  "fixed assets are excluded by convention.)")

    lines.append("")
    lines.append("(e) Form type & due date concluded:")
    lines.append(f"  {decision.reasoning}")
    if decision.needs_date_confirmation:
        lines.append("  ** Due date NOT auto-filled — assessment year is outside the "
                     "A.Y. 2026-27 table; confirm statutory dates afresh. **")
    if client.profile.notes:
        lines.append("")
        lines.append("Additional notes:")
        lines.append(f"  {client.profile.notes}")

    lines.append("")
    return "\n".join(lines)
