"""Fix the wire transfer provider's pending_msg + clean duplicate transactions.

The pending_msg got cleared (False) which means the portal can't display
the IBAN/instructions to the customer. Re-set with the LCL IBAN + reference
placeholder used by Odoo's standard wire transfer template.

Also cleans up duplicate 'pending' transactions on order S00468 left from
testing — only the most recent one is kept.

Run: python step29_fix_pending_msg_and_cleanup.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, write, unlink

# 1. Get LCL bank info
companies = search_read("res.company", [], ["id", "partner_id"])
partner_id = companies[0]["partner_id"][0]
banks = search_read("res.partner.bank", [("partner_id", "=", partner_id)],
                    ["acc_number", "bank_id"])
if banks:
    iban = banks[0]["acc_number"]
    bank = banks[0]["bank_id"][1] if banks[0]["bank_id"] else "LCL"
else:
    iban = "FR58 3000 2028 8000 0007 1073 R40"
    bank = "LCL"
print(f"IBAN: {iban} ({bank})")

# 2. Set proper pending_msg — Odoo will replace the QR widget separately,
#    we just need the IBAN + instructions in human-readable HTML.
pending_msg = f"""<p>
Merci pour votre commande. Votre devis sera confirmé dès réception du virement.
</p>
<p>
Effectuez votre virement sur le compte ci-dessous en utilisant la référence du devis (visible plus bas) en libellé.
</p>
<table style="width: 100%; max-width: 480px; margin-top: 1rem; border-collapse: collapse;">
  <tr><td style="padding: 0.4rem 0; color: #666;">Bénéficiaire</td><td style="padding: 0.4rem 0; font-weight: 600;">SARL STARTEC (MY.LAB)</td></tr>
  <tr><td style="padding: 0.4rem 0; color: #666;">Banque</td><td style="padding: 0.4rem 0; font-weight: 600;">{bank}</td></tr>
  <tr><td style="padding: 0.4rem 0; color: #666;">IBAN</td><td style="padding: 0.4rem 0; font-weight: 600; font-family: monospace;">{iban}</td></tr>
  <tr><td style="padding: 0.4rem 0; color: #666;">BIC</td><td style="padding: 0.4rem 0; font-weight: 600;">CRLYFRPP</td></tr>
</table>"""

write("payment.provider", [19], {"pending_msg": pending_msg})
print("✓ pending_msg restored on provider 19")
print()

# 3. Clean up duplicate pending transactions — keep only the most recent
#    one per order (Odoo will reuse it instead of creating a new -N).
print("=== Pending transaction cleanup ===")
all_pending = search_read("payment.transaction",
                          [("state", "=", "pending")],
                          ["id", "reference", "sale_order_ids", "create_date"])
# Group by order
by_order: dict[int, list[dict]] = {}
for t in all_pending:
    for so_id in t["sale_order_ids"]:
        by_order.setdefault(so_id, []).append(t)

to_delete = []
for so_id, txs in by_order.items():
    txs.sort(key=lambda x: x["create_date"], reverse=True)
    keep = txs[0]
    drop = txs[1:]
    print(f"  Order {so_id}: keep [{keep['id']}] {keep['reference']}, "
          f"drop {[t['reference'] for t in drop]}")
    to_delete.extend([t["id"] for t in drop])

if to_delete:
    unlink("payment.transaction", to_delete)
    print(f"✓ Deleted {len(to_delete)} duplicate transactions")
else:
    print("  (no duplicates)")

print()
print("=== Try again ===")
print("https://odoo.startec-paris.com/my/orders/435?access_token=9e296ee4-6c7e-4855-afe5-d5256e74ea22")
