"""ITR form type and statutory due date (system prompt §4).

The due-date table below is A.Y. 2026-27 specific.  For any other assessment
year :func:`determine_form_and_due_date` refuses to invent a date and asks the
caller to confirm the statutory dates afresh, exactly as the prompt requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .model import Profile

AY_WITH_KNOWN_DATES = "2026-27"

# Due dates for A.Y. 2026-27.
DUE_DATE_NON_AUDIT_NO_BUSINESS = "31 JULY 2026"
DUE_DATE_NON_AUDIT_BUSINESS = "31 AUGUST 2026"
DUE_DATE_TAX_AUDIT = "31 OCTOBER 2026"


@dataclass
class FormDecision:
    form: str
    due_date: str
    reasoning: str
    needs_date_confirmation: bool = False


def determine_form_and_due_date(profile: Profile, assessment_year: str) -> FormDecision:
    """Pick the likely ITR form and the matching due date with reasoning."""
    has_presumptive = profile.presumptive_44ad or profile.presumptive_44ada
    has_business = profile.has_business or has_presumptive

    # ---- form ----
    if profile.tax_audit_44ab:
        form = "ITR-3"
        form_reason = "tax audit applies u/s 44AB"
    elif has_presumptive and profile.has_capital_gains:
        # capital gains alongside presumptive income forces ITR-3, not ITR-4
        form = "ITR-3"
        form_reason = "presumptive income with capital gains forces ITR-3 (ITR-4 cannot report capital gains)"
    elif has_presumptive:
        form = "ITR-4"
        form_reason = "presumptive business/profession u/s 44AD/44ADA, no audit"
    elif has_business:
        form = "ITR-3"
        form_reason = "non-audit business/profession income"
    else:
        form = "ITR-2" if profile.has_capital_gains else "ITR-1"
        form_reason = ("salary / pension / other sources with capital gains"
                       if profile.has_capital_gains
                       else "salary / pension / other sources, no business")

    # ---- due date ----
    if profile.tax_audit_44ab:
        due, due_reason = DUE_DATE_TAX_AUDIT, "tax-audit case u/s 44AB"
    elif has_business:
        due, due_reason = DUE_DATE_NON_AUDIT_BUSINESS, "non-audit business/profession"
    else:
        due, due_reason = DUE_DATE_NON_AUDIT_NO_BUSINESS, "no business income"

    needs_confirm = assessment_year.strip() != AY_WITH_KNOWN_DATES
    if needs_confirm:
        due = "____ (confirm statutory date for A.Y. %s)" % (assessment_year or "?")
        due_reason += (f"; due dates above are A.Y. {AY_WITH_KNOWN_DATES}-specific — "
                       f"confirm afresh for A.Y. {assessment_year or '?'}")

    extra = ""
    if profile.section_10_26:
        extra = " Section 10(26) tribal exemption may apply (noted; does not change the list)."
    reasoning = f"Form {form}: {form_reason}. Due {due}: {due_reason}.{extra}"
    return FormDecision(form=form, due_date=due, reasoning=reasoning,
                        needs_date_confirmation=needs_confirm)
