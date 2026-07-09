"""Probe payment reconciliation of invoice 456 so we can restore it after reset."""
from _client import search_read, execute

# Receivable line(s) of the invoice
lines = search_read(
    "account.move.line",
    [("move_id", "=", 456)],
    ["id", "account_id", "name", "debit", "credit", "balance",
     "amount_residual", "reconciled", "full_reconcile_id",
     "matched_debit_ids", "matched_credit_ids"],
)
print("=== INVOICE 456 LINES ===")
for l in lines:
    print(l)

# Identify receivable line
recv = [l for l in lines if (l.get("matched_credit_ids") or l.get("matched_debit_ids"))]
print("\n=== RECONCILED LINE(S) ===")
for l in recv:
    print(l)
    # partial reconciliations
    parts = execute("account.partial.reconcile", "read",
                    [l["matched_credit_ids"] + l["matched_debit_ids"]],
                    {"fields": ["id", "debit_move_id", "credit_move_id", "amount"]})
    for p in parts:
        print("  partial:", p)
        # the counterpart payment line
        for fld in ("debit_move_id", "credit_move_id"):
            mlid = p[fld][0]
            ml = search_read("account.move.line", [("id", "=", mlid)],
                             ["id", "move_id", "account_id", "debit", "credit",
                              "payment_id", "parent_state"])
            print(f"    {fld}: {ml}")
