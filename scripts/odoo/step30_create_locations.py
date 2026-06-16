"""Création des locations stock : MYVO/Stock/Bulk, MYVO/Stock/Packaging, MYVO/Stock/Fini.

Idempotent : skip si une location avec le même nom existe déjà sous le même parent.

Note: le warehouse principal de cette instance Odoo a le code 'MYVO' (pas 'WH').
La location Stock racine est donc 'MYVO/Stock'. Le script trouve dynamiquement
cette location Stock via son nom + usage internal + parent = view_location du
warehouse principal, sans hardcoder le code warehouse.
"""
from scripts.odoo._client import execute, search_read, create

LOCATIONS = [
    {"name": "Bulk", "usage": "internal"},
    {"name": "Packaging", "usage": "internal"},
    {"name": "Fini", "usage": "internal"},
]


def get_main_stock_location() -> int:
    """Trouve la location racine 'Stock' sous le warehouse principal.
    Adapté pour fonctionner quel que soit le code du warehouse (MYVO, WH, etc.)."""
    # Lister tous les warehouses (typiquement 1 seul) et récupérer leur view_location_id
    warehouses = search_read("stock.warehouse", [], ["id", "name", "code", "view_location_id"], limit=1)
    if not warehouses:
        raise RuntimeError("Aucun warehouse — vérifier la configuration Inventory")
    wh = warehouses[0]
    view_loc_id = wh["view_location_id"][0]  # field is many2one [id, name]
    print(f"Warehouse: {wh['code']} ({wh['name']}), view_location_id={view_loc_id}")

    # Trouver la sous-location 'Stock' (usage=internal) sous cette view
    stock_locs = search_read("stock.location", [
        ("location_id", "=", view_loc_id),
        ("usage", "=", "internal"),
        ("name", "=", "Stock"),
    ], ["id", "complete_name"])
    if not stock_locs:
        raise RuntimeError(f"Location 'Stock' introuvable sous view_location_id={view_loc_id}")
    return stock_locs[0]["id"]


def main():
    parent_id = get_main_stock_location()
    # Récupérer le complete_name du parent pour logging
    parent_info = search_read("stock.location", [("id", "=", parent_id)], ["complete_name"])
    parent_name = parent_info[0]["complete_name"]
    print(f"Parent location: {parent_name} (id={parent_id})")

    created, skipped = 0, 0
    for loc in LOCATIONS:
        existing = search_read("stock.location", [
            ("location_id", "=", parent_id),
            ("name", "=", loc["name"]),
        ], ["id", "complete_name"])
        if existing:
            print(f"  [SKIP] {existing[0]['complete_name']} (id={existing[0]['id']})")
            skipped += 1
            continue
        new_id = create("stock.location", {
            "name": loc["name"],
            "usage": loc["usage"],
            "location_id": parent_id,
        })
        print(f"  [CREATE] {parent_name}/{loc['name']} (id={new_id})")
        created += 1
    print(f"\nDone. Created: {created}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
