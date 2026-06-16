"""Confirme + assigne le nouveau BL 149 (MYVO/OUT/00132) pour qu'il soit prêt à traiter."""
from _client import execute, search_read

NEW = 149

execute("stock.picking", "action_confirm", [[NEW]])
execute("stock.picking", "action_assign", [[NEW]])

p = search_read("stock.picking", [("id", "=", NEW)],
                ["name", "state", "partner_id", "origin"])[0]
print(f"=== {p['name']} | state={p['state']} | {p['partner_id']} | origin={p['origin']} ===")

mv = search_read("stock.move", [("picking_id", "=", NEW)],
                 ["product_id", "product_uom_qty", "quantity", "state"])
print("\n=== moves (réservé) ===")
for m in mv:
    print(f"  {m['product_id'][1][:42]:42} demande={m['product_uom_qty']} réservé={m.get('quantity')} state={m['state']}")

# état SO côté livraison
so = search_read("sale.order", [("id", "=", 533)], ["name", "picking_ids", "delivery_status"])[0]
print(f"\nSO {so['name']} pickings={so['picking_ids']} delivery_status={so.get('delivery_status')}")
