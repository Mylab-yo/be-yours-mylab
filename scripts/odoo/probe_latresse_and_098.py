"""Verify (1) LA TRESSE FAC/00103 really due, (2) FAC/00098 virement received."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read

# ── LA TRESSE ───────────────────────────────────────────────────────────────
print("=== LA TRESSE FAC/2026/00103 ===")
inv = search_read("account.move", [("name", "=", "FAC/2026/00103")],
                  ["id", "partner_id", "amount_total", "amount_residual",
                   "payment_state", "invoice_date", "invoice_date_due"])[0]
print(inv)
pid = inv["partner_id"][0]
cp = search_read("res.partner", [("id", "=", pid)], ["commercial_partner_id"])[0]
cpid = cp["commercial_partner_id"][0]

# All open (unreconciled) receivable lines for this commercial partner
print("\n-- Open receivable items (partner ledger) --")
lines = search_read("account.move.line",
    [("partner_id", "child_of", cpid),
     ("account_id.account_type", "=", "asset_receivable"),
     ("parent_state", "=", "posted"), ("reconciled", "=", False)],
    ["move_id", "name", "debit", "credit", "amount_residual", "date"])
for l in lines:
    print(f"   {l['move_id'][1]} | {l['name']} | dr{l['debit']} cr{l['credit']} "
          f"| residual={l['amount_residual']} | {l['date']}")

# Payments for this partner
print("\n-- Payments --")
pays = search_read("account.payment",
    [("partner_id", "child_of", cpid), ("payment_type", "=", "inbound")],
    ["name", "amount", "state", "journal_id", "is_reconciled", "date", "memo"])
for p in pays:
    print(f"   {p['name']} {p['amount']}€ {p['journal_id'][1]} "
          f"reconciled={p['is_reconciled']} {p.get('date')} memo={p.get('memo')!r}")

# ── FAC/00098 virement ──────────────────────────────────────────────────────
print("\n\n=== FAC/2026/00098 (virement #3491) ===")
inv98 = search_read("account.move", [("name", "=", "FAC/2026/00098")],
                    ["id", "partner_id", "amount_total", "amount_residual",
                     "payment_state", "invoice_date_due"])[0]
print(inv98)

# Search LCL/bank statement lines matching 963.36 (unreconciled)
print("\n-- Bank statement lines ~963.36 € --")
amt = inv98["amount_total"]
bsl = search_read("account.bank.statement.line",
    [("amount", ">=", amt - 0.5), ("amount", "<=", amt + 0.5)],
    ["id", "date", "payment_ref", "partner_id", "amount", "journal_id",
     "is_reconciled"])
for b in bsl:
    print(f"   {b['date']} | {b['payment_ref']} | {b.get('partner_id')} "
          f"| {b['amount']}€ | {b['journal_id'][1]} | reconciled={b['is_reconciled']}")
if not bsl:
    print("   none found at this amount")

# Any payment for E.Leclerc partner?
pid98 = inv98["partner_id"][0]
cp98 = search_read("res.partner", [("id", "=", pid98)], ["commercial_partner_id"])[0]["commercial_partner_id"][0]
print("\n-- Payments for E.Leclerc partner --")
pays98 = search_read("account.payment",
    [("partner_id", "child_of", cp98), ("payment_type", "=", "inbound")],
    ["name", "amount", "state", "journal_id", "is_reconciled", "date", "memo"])
for p in pays98:
    print(f"   {p['name']} {p['amount']}€ {p['journal_id'][1]} "
          f"reconciled={p['is_reconciled']} {p.get('date')} memo={p.get('memo')!r}")
if not pays98:
    print("   no inbound payment")
