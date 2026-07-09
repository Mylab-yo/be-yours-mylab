"""Installation des modules Odoo prérequis pour le MRP stock setup.

Idempotent : skip si module déjà installed. button_immediate_install() peut
prendre 10-30s par module et redémarre les workers — ne pas paralléliser.

Order: purchase → purchase_stock (bridge, crée la route Buy) → mrp (crée Manufacture).
"""
from scripts.odoo._client import execute, search_read

MODULES = ["purchase", "purchase_stock", "mrp"]


def main():
    print("Installing Odoo modules...")
    for name in MODULES:
        rows = search_read("ir.module.module", [("name", "=", name)], ["id", "state"])
        if not rows:
            print(f"  [MISSING] {name} module introuvable dans ir.module.module")
            continue
        mod_id = rows[0]["id"]
        state = rows[0]["state"]
        if state == "installed":
            print(f"  [SKIP] {name} déjà installed (id={mod_id})")
            continue
        if state == "uninstalled":
            print(f"  [INSTALL] {name} (id={mod_id})... cela peut prendre 30s")
            execute("ir.module.module", "button_immediate_install", [[mod_id]])
            # Re-read pour confirmer
            new_state = search_read("ir.module.module", [("id", "=", mod_id)], ["state"])[0]["state"]
            print(f"  [OK]      {name} state={new_state}")
        else:
            print(f"  [WARN] {name} en état {state} — intervention manuelle requise")

    # Après installation, lister les routes pour confirmer Buy + Manufacture
    print("\nRoutes après installation :")
    for r in search_read("stock.route", [], ["id", "name"]):
        print(f"  {r['id']}: {r['name']}")


if __name__ == "__main__":
    main()
