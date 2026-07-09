"""Pose les SKU POMPE-200 / POMPE-500 / POMPE-1000 sur les pompes Odoo
reutilisees par le storefront. Idempotent : ne reecrit que si different."""
from _client import search_read, write

# variant_id -> (sku, prix HT attendu)
TARGETS = {
    2486: ("POMPE-200", 0.50),   # Pompe 200ml
    2410: ("POMPE-500", 0.50),   # Pompe 500ml
    2564: ("POMPE-1000", 1.00),  # Pompe 1000ml (SKU normalement deja pose)
}

for var_id, (sku, price) in TARGETS.items():
    rows = search_read("product.product", [("id", "=", var_id)],
                       ["id", "name", "default_code", "lst_price", "sale_ok", "taxes_id"])
    if not rows:
        print(f"var {var_id}: INTROUVABLE"); continue
    p = rows[0]
    updates = {}
    if p.get("default_code") != sku:
        updates["default_code"] = sku
    if not p.get("sale_ok"):
        updates["sale_ok"] = True
    if 103 not in (p.get("taxes_id") or []):
        updates["taxes_id"] = [(6, 0, [103])]  # 20% G
    if updates:
        write("product.product", [var_id], updates)
        print(f"var {var_id} ({p['name']}): MAJ {list(updates)}")
    else:
        print(f"var {var_id} ({p['name']}): deja OK (sku={p.get('default_code')}, "
              f"prix={p.get('lst_price')}, sale_ok={p.get('sale_ok')})")
    if abs((p.get("lst_price") or 0) - price) > 0.001:
        print(f"  [WARN] prix Odoo {p.get('lst_price')} != attendu {price} -- verifier manuellement")
