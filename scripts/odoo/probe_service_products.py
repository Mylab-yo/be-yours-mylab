"""Verifier les noms exacts des produits services dans Odoo (dossier cosmeto, etiquettes, impression)."""
from scripts.odoo._client import search_read

queries = [
    "dossier",
    "cosmetologique",
    "etiquette",
    "impression",
]

print("=== Produits services recherches ===\n")
for q in queries:
    print(f"--- ilike '{q}' ---")
    rows = search_read(
        "product.product",
        [("name", "ilike", q), ("sale_ok", "=", True)],
        ["id", "name", "default_code", "list_price"],
    )
    for r in rows:
        print(f"  [{r['id']:5d}]  name={r['name']!r}  code={r.get('default_code') or '-'}  price={r['list_price']}")
    print()
