"""Clean JE 660 : delete only the duplicate non-tax lines (2074 mine + 2076 suspense).
Keep 2072 (D 411), 2073 (C 707 with tax_ids), 2075 (auto C TVA)."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute, write

JE_ID = 660
ORPHAN_LINE_ID = 2046
TO_DELETE = [2074, 2076]

# State check
je = search_read("account.move", [("id", "=", JE_ID)], ["state", "name"], limit=1)
print(f"JE state: {je[0]}")

# Delete via write line_ids
write("account.move", [JE_ID], {"line_ids": [(2, lid, 0) for lid in TO_DELETE]})
print(f"  Deleted {TO_DELETE}")

# Verify
lines = search_read("account.move.line", [("move_id", "=", JE_ID)],
                    ["id", "account_id", "debit", "credit", "tax_ids", "tax_line_id"], limit=20)
print(f"\n=== After cleanup ({len(lines)} lines) ===")
total_d, total_c = 0, 0
for l in lines:
    print(f"  line {l['id']}: acct={l['account_id'][1][:35]:<35} D={l['debit']:>7.2f} C={l['credit']:>7.2f} tax_ids={l['tax_ids']} tax_line={l.get('tax_line_id')}")
    total_d += l["debit"]
    total_c += l["credit"]
print(f"  TOTAL: D={total_d:.2f} C={total_c:.2f} balanced={abs(total_d - total_c) < 0.01}")

# Post
print("\n=== Re-post ===")
execute("account.move", "action_post", [JE_ID])
je = search_read("account.move", [("id", "=", JE_ID)], ["name", "state"], limit=1)
print(f"  {je[0]}")

# Re-reconcile
debit_line = next(l for l in lines if l["account_id"][0] == 887)
print(f"\n=== Re-reconcile line {debit_line['id']} with {ORPHAN_LINE_ID} ===")
execute("account.move.line", "reconcile", [[debit_line["id"], ORPHAN_LINE_ID]])

orphan_final = search_read("account.move.line", [("id", "=", ORPHAN_LINE_ID)],
                           ["amount_residual", "reconciled"], limit=1)
print(f"  Orphan final: {orphan_final[0]}")

# Final balance
print("\n=== Partner 1074 receivable (open posted) ===")
open_lines = search_read("account.move.line",
                         [("partner_id", "=", 1074),
                          ("account_id", "=", 887),
                          ("reconciled", "=", False),
                          ("parent_state", "=", "posted")],
                         ["id", "move_id", "name", "amount_residual"], limit=20)
total = 0
for l in open_lines:
    total += l["amount_residual"]
    print(f"  {l}")
print(f"  NET: {total:.2f} €  (should be 2666.68€ = FAC/2026/00103)")
