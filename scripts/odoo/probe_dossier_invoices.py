"""Trouver les factures qui contiennent le produit dossier cosmetologique (id=2313)."""
from scripts.odoo._client import search_read

# Find invoice lines with product 2313
lines = search_read(
    "account.move.line",
    [("product_id", "=", 2313),
     ("move_id.move_type", "in", ["out_invoice", "out_receipt"])],
    ["move_id", "product_id", "name", "price_subtotal"],
)
move_ids = list({l["move_id"][0] for l in lines})
print(f"=== {len(lines)} ligne(s) avec produit dossier cosmeto, sur {len(move_ids)} facture(s) ===\n")

if not move_ids:
    print("(aucune facture trouvee — peut-etre uniquement sur sale.order ou pas encore facture ?)")
else:
    moves = search_read(
        "account.move",
        [("id", "in", move_ids)],
        ["id", "name", "partner_id", "state", "payment_state", "amount_total", "invoice_date"],
    )
    for m in sorted(moves, key=lambda x: x.get("invoice_date") or "", reverse=True)[:15]:
        partner = m["partner_id"][1] if m["partner_id"] else "(no partner)"
        print(f"  [{m['id']:5d}] {m['name']:25s} | {m['invoice_date']!s:12s} | state={m['state']:8s} pay={m['payment_state']:10s} | {m['amount_total']:>8.2f} EUR | {partner}")

print("\n=== Et sur les sale.order (pas encore facture) ? ===\n")
so_lines = search_read(
    "sale.order.line",
    [("product_id", "=", 2313)],
    ["order_id", "name", "price_subtotal"],
)
so_ids = list({l["order_id"][0] for l in so_lines})
if so_ids:
    sos = search_read(
        "sale.order",
        [("id", "in", so_ids)],
        ["id", "name", "partner_id", "state", "invoice_status", "amount_total", "date_order"],
    )
    for s in sorted(sos, key=lambda x: x.get("date_order") or "", reverse=True)[:15]:
        partner = s["partner_id"][1] if s["partner_id"] else "(no partner)"
        print(f"  [{s['id']:5d}] {s['name']:15s} | {s['date_order']!s:20s} | state={s['state']:8s} inv={s['invoice_status']:14s} | {s['amount_total']:>8.2f} EUR | {partner}")
