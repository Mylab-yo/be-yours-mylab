"""Quand un BL (stock.picking) est-il cree pour une commande ? Ratio global + cas matches."""
from collections import Counter
from scripts.odoo._client import search_read, execute

# 1) Etat des commandes matchees dans le dry-run
matched_orders = ["S00521","S00537","S00543","S00553","S00555","S00560",
                  "S00573","S00575","S00579","S00580","S00581"]
print("=== Commandes matchees : etat + nb BL ===")
sos = search_read("sale.order", [("name", "in", matched_orders)],
    ["name", "state", "delivery_count", "picking_ids"], limit=50)
for s in sorted(sos, key=lambda x: x["name"]):
    print(f"  {s['name']}  state={s['state']:<10} delivery_count={s.get('delivery_count')} "
          f"pickings={s.get('picking_ids')}")

# 2) Photo globale : repartition des commandes par etat
print("\n=== Repartition de TOUTES les sale.order par etat ===")
all_states = search_read("sale.order", [], ["state"], limit=5000)
print("  ", dict(Counter(s["state"] for s in all_states)))

# 3) Parmi les commandes CONFIRMEES (state=sale), combien ont >=1 BL ?
confirmed = search_read("sale.order", [("state", "=", "sale")],
    ["name", "delivery_count"], limit=5000)
with_bl = [s for s in confirmed if (s.get("delivery_count") or 0) > 0]
print(f"\n=== Commandes confirmees (state=sale) : {len(confirmed)} ===")
print(f"  avec >=1 BL : {len(with_bl)}  |  sans BL : {len(confirmed) - len(with_bl)}")

# 4) Echantillon de confirmees SANS BL -> pourquoi ? (types de produits)
sans_bl = [s for s in confirmed if (s.get("delivery_count") or 0) == 0][:5]
if sans_bl:
    print("\n=== Echantillon confirmees SANS BL (pourquoi pas de picking ?) ===")
    for s in sans_bl:
        full = search_read("sale.order", [("name", "=", s["name"])],
            ["name", "order_line"], limit=1)[0]
        lines = search_read("sale.order.line", [("order_id.name", "=", s["name"])],
            ["product_id", "product_type"], limit=20) if full.get("order_line") else []
        types = Counter(l.get("product_type") for l in lines)
        print(f"  {s['name']}: types produits = {dict(types)}")

# 5) Etat des BL des commandes confirmees (combien deja done/valides ?)
print("\n=== Etat des BL sortants existants ===")
pk_states = search_read("stock.picking", [("picking_type_code","=","outgoing")],
    ["state"], limit=5000)
print("  ", dict(Counter(p["state"] for p in pk_states)))
