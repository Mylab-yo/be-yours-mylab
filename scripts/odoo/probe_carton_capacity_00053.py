"""Lire x_carton_capacity pour tous les produits de MYVO/OUT/00053."""
from scripts.odoo._client import search_read

skus = [
    "shampoing-nourrissant-500-ml",
    "shampoing-purifiant-500-ml",
    "shampoing-ha-repulpe-500-ml",
    "masque-nourrissant-400-ml",
    "masque-volume-400-ml",
    "bain-miraculeux-50-ml",
    "shampoing-nourrissant-200-ml",
    "shampoing-purifiant-200-ml",
    "shampoing-ha-repulpe-200-ml",
    "masque-nourrissant-200-ml",
    "masque-volume-200-ml",
]

print(f"{'SKU':40s} | {'cap':>5s} | {'weight':>7s} | name")
for sku in skus:
    rows = search_read(
        "product.template",
        [("default_code", "=", sku)],
        ["id", "name", "default_code", "x_carton_capacity", "weight"],
    )
    if rows:
        r = rows[0]
        cap = r.get("x_carton_capacity")
        w = r.get("weight")
        print(f"{sku:40s} | {str(cap):>5s} | {w:>7} | {r['name']}")
    else:
        print(f"{sku:40s} | NOT FOUND")

# Pompes (probably different SKU)
print()
pompes = search_read(
    "product.template",
    [("name", "ilike", "pompe")],
    ["id", "name", "default_code", "x_carton_capacity", "weight"],
)
print("=== Pompes products ===")
for r in pompes:
    print(f"  #{r['id']} | code={r['default_code']} | cap={r.get('x_carton_capacity')} | w={r.get('weight')} | {r['name']}")
