"""Clean up JE 660 : reset to draft, remove tax_ids that triggered auto-lines, re-post + reconcile."""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute, write, create, unlink

JE_ID = 660
ORPHAN_LINE_ID = 2046

# 1. Inspect current state
print("=== Current JE state ===")
je = search_read("account.move", [("id", "=", JE_ID)], ["state", "name"], limit=1)
print(f"  {je[0]}")
lines = search_read("account.move.line", [("move_id", "=", JE_ID)],
                    ["id", "account_id", "debit", "credit", "tax_ids", "tax_line_id", "reconciled"],
                    limit=20)
for l in lines:
    print(f"  line {l['id']}: acct={l['account_id'][1][:30]:<30} D={l['debit']:>7.2f} C={l['credit']:>7.2f} tax_ids={l['tax_ids']} tax_line={l.get('tax_line_id')} rec={l.get('reconciled')}")

# 2. Reset to draft - this should undo the reconciliation
print("\n=== Reset to draft ===")
try:
    execute("account.move", "button_draft", [JE_ID])
    je = search_read("account.move", [("id", "=", JE_ID)], ["state"], limit=1)
    print(f"  state now: {je[0]['state']}")
except Exception as e:
    print(f"  ERROR draft: {e}")
    # Try removing reconcile manually first
    print("  Trying remove_move_reconcile...")
    execute("account.move.line", "remove_move_reconcile", [[l["id"] for l in lines if l.get("reconciled")]])
    execute("account.move", "button_draft", [JE_ID])
    je = search_read("account.move", [("id", "=", JE_ID)], ["state"], limit=1)
    print(f"  state now: {je[0]['state']}")

# Verify orphan is back
orphan = search_read("account.move.line", [("id", "=", ORPHAN_LINE_ID)],
                     ["amount_residual", "reconciled"], limit=1)
print(f"  Orphan line 2046 after draft: residual={orphan[0]['amount_residual']} reconciled={orphan[0]['reconciled']}")

# 3. Remove all lines on JE
print("\n=== Delete all lines + recreate clean ===")
lines_to_delete = search_read("account.move.line", [("move_id", "=", JE_ID)], ["id"], limit=20)
line_ids = [l["id"] for l in lines_to_delete]
# Use write with [(2, id, 0)] tuples to delete
delete_commands = [(2, lid, 0) for lid in line_ids]
write("account.move", [JE_ID], {"line_ids": delete_commands})
print(f"  Deleted {len(line_ids)} old lines")

# 4. Recreate clean: 3 lines, NO tax_ids, NO tax_line_id
new_lines = [
    (0, 0, {
        "account_id": 887,  # 411100
        "partner_id": 1074,
        "name": "Neutralisation crédit orphelin (paiement 11/04/2026 - devis 300582)",
        "debit": 77.98,
        "credit": 0.0,
    }),
    (0, 0, {
        "account_id": 1223,  # 707000
        "partner_id": 1074,
        "name": "Régularisation CA - avoir intégré dans FAC S00418 déjà compensé par crédit existant",
        "debit": 0.0,
        "credit": 64.98,
    }),
    (0, 0, {
        "account_id": 933,  # 445710
        "partner_id": 1074,
        "name": "Régularisation TVA 20% G sur 64.98€ (rétablissement)",
        "debit": 0.0,
        "credit": 13.00,
    }),
]
write("account.move", [JE_ID], {"line_ids": new_lines})
print("  Re-added 3 clean lines")

# Verify
lines = search_read("account.move.line", [("move_id", "=", JE_ID)],
                    ["id", "account_id", "debit", "credit", "tax_ids", "tax_line_id"], limit=20)
print(f"\n=== After cleanup ({len(lines)} lines) ===")
total_d, total_c = 0, 0
for l in lines:
    print(f"  line {l['id']}: acct={l['account_id'][1][:35]:<35} D={l['debit']:>7.2f} C={l['credit']:>7.2f}")
    total_d += l["debit"]
    total_c += l["credit"]
print(f"  TOTAL: D={total_d:.2f} C={total_c:.2f}  balanced={total_d == total_c}")

# 5. Post
print("\n=== Re-post ===")
execute("account.move", "action_post", [JE_ID])
je = search_read("account.move", [("id", "=", JE_ID)], ["name", "state"], limit=1)
print(f"  {je[0]}")

# 6. Re-reconcile
print("\n=== Re-reconcile ===")
debit_line = next(l for l in lines if l["account_id"][0] == 887)
print(f"  Reconciling line {debit_line['id']} with orphan line {ORPHAN_LINE_ID}")
execute("account.move.line", "reconcile", [[debit_line["id"], ORPHAN_LINE_ID]])

# Verify final
orphan_final = search_read("account.move.line", [("id", "=", ORPHAN_LINE_ID)],
                           ["amount_residual", "reconciled"], limit=1)
print(f"  Orphan final: {orphan_final[0]}")

# Show partner balance
print("\n=== Final partner 1074 receivable balance (open posted lines) ===")
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
print(f"  NET: {total:.2f} €")

print(f"\n👉 JE: https://odoo.startec-paris.com/odoo/action-account.action_move_journal_line/{JE_ID}")
