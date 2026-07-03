"""Config picking-type + quants sans lot pour les 4 lignes lot-less de MYVO/OUT/00045."""
from _client import search_read

# 1. picking type config (force lot ?)
pt = search_read("stock.picking.type", [("id", "=", 10)],
                 ["name", "code", "use_create_lots", "use_existing_lots"])[0]
print(f"=== picking.type {pt['name']} code={pt['code']} ===")
print(f"  use_create_lots={pt['use_create_lots']} use_existing_lots={pt['use_existing_lots']}")

# 2. quants des 4 produits lot-less (id product.product)
FOUR = {
    2396: "shampoing nourrissant 200ml",
    2357: "masque nourrissant 200ml",
    2403: "shampoing volume 200ml",
    2427: "shampoing nourrissant 1000ml",
}
print("\n=== quants (on-hand) des 4 produits ===")
for pid, label in FOUR.items():
    quants = search_read("stock.quant",
                         [("product_id", "=", pid), ("location_id.usage", "=", "internal")],
                         ["location_id", "lot_id", "quantity", "reserved_quantity"])
    print(f"\n  [{pid}] {label}")
    if not quants:
        print("    (aucun quant interne)")
    for q in quants:
        print(f"    loc={q['location_id'][1]} lot={q.get('lot_id')} "
              f"qty={q['quantity']} reserved={q['reserved_quantity']}")
