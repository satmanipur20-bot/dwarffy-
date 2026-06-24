# SAT ITR Requirement List Generator

A reusable generator for **Shree Accounting & Taxation (SAT)** that turns a
client's extracted bank/investment data into the firm's branded, one-page
**Requirement List** (`.xlsx`) plus a **reconciliation memo** (`.txt`) flagging
anything that needs the firm's confirmation.

It implements the firm's house rules from
[`SAT_ITR_Requirement_List_Prompt.md`](SAT_ITR_Requirement_List_Prompt.md):
collect every bank account / investment across the three source documents,
normalise & de-duplicate them, decide the ITR form and due date, and render the
document on the branded template (logo + letterhead preserved).

## Install

```bash
pip install -r requirements.txt   # just openpyxl
```

## Usage

```bash
python -m satrl.cli examples/nitin_kumar_jain.json --outdir examples/output
```

This writes, next to each other:

* `Requirement_<ClientName>_FY_<years>.xlsx` — the branded one-page list
* `Requirement_<ClientName>_FY_<years>_memo.txt` — the reconciliation memo

### Local web UI

```bash
python app.py                 # http://localhost:5000
PORT=8080 python app.py       # custom port
```

Open the address in a browser, paste or upload a client JSON spec, click
**Generate**, then download the `.xlsx` and the memo. The form is pre-filled
with the Nitin Kumar Jain example.

### As a library

```python
from satrl import load_client_file, build_requirement_xlsx, build_reconciliation_memo

client, bank_diag, inv_diag = load_client_file("examples/nitin_kumar_jain.json")
decision = build_requirement_xlsx(client, "out.xlsx")
memo = build_reconciliation_memo(client, bank_diag, inv_diag, decision)
print(decision.form, decision.due_date)
```

## Input format

You supply a JSON spec transcribing what each of the three source documents
shows — the previous-year **balance sheet**, the **AIS**, and the **computation
of income**. The generator does the normalisation, de-duplication, form
determination and reconciliation itself.

```jsonc
{
  "particulars": {
    "name": "NITIN KUMAR JAIN", "pan": "AFCPJ2469P",
    "status": "Individual",            // or "HUF"
    "gender": "male",                  // picks "Sir" / "Madam"
    "assessment_year": "2026-27",
    "previous_year": "2025-26 (01.04.2025 to 31.03.2026)",
    "address": "Thangal Bazar, Imphal West, Manipur - 795001"
  },
  "profile": {                          // decides ITR form + due date
    "has_business": true,
    "presumptive_44ad": false, "presumptive_44ada": false,
    "has_capital_gains": false,
    "tax_audit_44ab": true,
    "gst_turnover": null,
    "section_10_26": false,             // Manipur tribal exemption (note only)
    "notes": "..."
  },
  "sources": {
    "ais":           { "bank_accounts": [...], "investments": [...] },
    "balance_sheet": { "bank_accounts": [...], "investments": [...] },
    "computation":   { "bank_accounts": [...], "investments": [...] }
  },
  "excluded_notes": ["Loans & advances ... excluded per firm convention."]
}
```

**Bank account** item: `{"bank", "account_type", "account_no", "branch"}`.

**Investment** item — either a ready-made label, or a structured `kind` that the
formatter turns into the column-B text:

```jsonc
{"kind": "fixed_deposit",  "entity": "Indian Overseas Bank", "ref": "0073204000002576"}
{"kind": "recurring_deposit", "entity": "Indian Overseas Bank", "branch": "CPRC, Chennai", "ref": "4875688424"}
{"kind": "mutual_fund", "entity": "ICICI Prudential", "rta": "CAMS", "ref": "34789546 / 40545926"}
{"kind": "gold", "ref": "—"}                 // "Gold & Jewellery (if made any investment)"
{"kind": "demat", "ref": "—"}                // Shares & Securities
{"label": "Post Office Recurring Deposit (RD)", "ref": "—"}   // verbatim label
{"kind": "fixed_deposit", "entity": "SBI", "ref": "123", "matured": true}  // excluded, noted in memo
```

Understood `kind`s: `fixed_deposit`, `recurring_deposit`, `kvp`, `nsc`, `bond`,
`share`/`demat`, `mutual_fund`, `lic`, `gold`.

## Rules implemented

| Area | Behaviour |
|---|---|
| **De-duplication** | Account/investment included if it appears in *any* source; merged across sources by first-seen order. |
| **Zero-padding** | Account numbers are text (leading zeros preserved). Padding differences are *normalised, not flagged*; the most-padded form is displayed. |
| **Bank merges** | United Bank of India→PNB, Allahabad→Indian Bank, Vijaya/Dena→Bank of Baroda. Paytm Payments Bank flagged as defunct. |
| **Exclusions** | Loans & advances, immovable property, fixed assets, and matured/closed instruments are kept out of the list (matured ones noted in the memo). |
| **Form & due date** | ITR-1/2 (31 Jul 2026), ITR-3/4 non-audit (31 Aug 2026), ITR-3 audit (31 Oct 2026). Capital gains + presumptive forces ITR-3. Dates are **A.Y. 2026-27 only** — any other year is left blank for confirmation. |
| **Memo** | Flags single-source items, genuine digit mismatches, matured/closed instruments, deliberate omissions, and records the form/due-date reasoning. |

## Output styling

The list is rendered on `templates/SAT_Requirement_Template.xlsx`, which carries
the embedded logo and the fixed letterhead. The generator rebuilds the data
region with the firm's colours (charcoal `#404042`, orange `#EB8025`,
light-orange `#FBE3CC`), alternating row fills, medium/thin borders, Calibri
throughout, gridlines off, landscape, fit-to-one-page. Column D (Remarks) is
left blank in every data row, per firm convention.

> **Note on QA:** to render the workbook to PDF for a visual one-page check, use
> `soffice --headless --convert-to pdf <file>.xlsx`. This requires LibreOffice's
> Calc filter, which is not available in every sandbox.

## Project layout

```
satrl/
  model.py       # dataclasses: Particulars, Profile, BankAccount, Investment, ClientData
  normalize.py   # bank merges, zero-pad keys, de-duplication + diagnostics
  forms.py       # ITR form + due-date decision
  builder.py     # renders the branded .xlsx on the template
  memo.py        # reconciliation memo
  loader.py      # JSON spec -> ClientData
  cli.py         # python -m satrl.cli
templates/
  SAT_Requirement_Template.xlsx   # branded scaffold (logo + letterhead)
examples/
  nitin_kumar_jain.json           # sample input
  output/                         # generated sample list + memo
```
