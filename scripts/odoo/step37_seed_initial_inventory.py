"""Saisie d'inventaire initial (stock.quant + action_apply_inventory).

Pour chaque ligne du CSV : cree un ajustement d'inventaire avec un lot si fourni.
Idempotent : si un quant existe deja pour le triplet (product, location, lot),
met a jour la quantite au lieu d'ajouter.

PRECONDITIONS:
- Le scheduler Odoo doit etre desactive (_disable_scheduler.py) avant de lancer
- Le CSV initial_inventory.csv doit etre rempli manuellement avec les vraies quantites
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write

CSV_PATH = Path(__file__).parent / "data" / "initial_inventory.csv"


def get_product_id(sku: str) -> int | None:
    rows = search_read("product.product", [("default_code", "=", sku)], ["id"])
    return rows[0]["id"] if rows else None


def get_location_id(complete_name: str) -> int:
    rows = search_read("stock.location", [("complete_name", "=", complete_name)], ["id"])
    if not rows:
        raise RuntimeError(f"Location {complete_name} introuvable")
    return rows[0]["id"]


def get_or_create_lot(product_id: int, lot_name: str) -> int | bool:
    if not lot_name:
        return False
    rows = search_read("stock.lot", [
        ("name", "=", lot_name),
        ("product_id", "=", product_id),
    ], ["id"])
    if rows:
        return rows[0]["id"]
    return create("stock.lot", {
        "name": lot_name,
        "product_id": product_id,
    })


def main():
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, updated, missing, skipped_empty, failed = 0, 0, 0, 0, 0
    fails = []
    for r in rows:
        sku = r["sku"].strip()
        loc_name = r["location"].strip()
        qty_raw = r["quantity"].strip()
        lot_name = r.get("lot_name", "").strip()

        if not qty_raw:
            print(f"  [SKIP-EMPTY] {sku}@{loc_name} (quantity vide)")
            skipped_empty += 1
            continue
        qty = float(qty_raw)

        pid = get_product_id(sku)
        if not pid:
            print(f"  [MISSING] {sku}")
            missing += 1
            continue

        try:
            loc_id = get_location_id(loc_name)
            lot_id = get_or_create_lot(pid, lot_name) if lot_name else False

            # Verifier si quant existe
            domain = [("product_id", "=", pid), ("location_id", "=", loc_id)]
            if lot_id:
                domain.append(("lot_id", "=", lot_id))
            else:
                domain.append(("lot_id", "=", False))
            existing = search_read("stock.quant", domain, ["id", "quantity"])

            if existing:
                write("stock.quant", [existing[0]["id"]], {"inventory_quantity": qty})
                execute("stock.quant", "action_apply_inventory", [existing[0]["id"]])
                print(f"  [UPDATE] {sku}@{loc_name}{f' lot={lot_name}' if lot_name else ''} -> {qty}")
                updated += 1
            else:
                new_id = create("stock.quant", {
                    "product_id": pid,
                    "location_id": loc_id,
                    "lot_id": lot_id or False,
                    "inventory_quantity": qty,
                })
                execute("stock.quant", "action_apply_inventory", [new_id])
                print(f"  [CREATE] {sku}@{loc_name}{f' lot={lot_name}' if lot_name else ''} = {qty}")
                created += 1
        except Exception as exc:
            print(f"  [FAILED] {sku}@{loc_name}: {str(exc)[:120]}")
            fails.append(sku)
            failed += 1

    print(f"\nDone. Created: {created}, Updated: {updated}, Skipped (empty): {skipped_empty}, "
          f"Missing: {missing}, Failed: {failed}")
    if fails:
        print("Echecs:", ", ".join(fails))


if __name__ == "__main__":
    main()
