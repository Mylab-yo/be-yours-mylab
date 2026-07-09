"""Creation des regles de reapprovisionnement (stock.warehouse.orderpoint).

Une regle par bulk + une regle par packaging.
Lit data/bulk_formulas.csv et data/packaging_products.csv.
Idempotent : match par (product_id, location_id).
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write

BULK_CSV = Path(__file__).parent / "data" / "bulk_formulas.csv"
PACK_CSV = Path(__file__).parent / "data" / "packaging_products.csv"


def get_product_id(sku: str) -> int | None:
    rows = search_read("product.product", [("default_code", "=", sku)], ["id"])
    return rows[0]["id"] if rows else None


def get_warehouse_id() -> int:
    rows = search_read("stock.warehouse", [], ["id"], limit=1)
    if not rows:
        raise RuntimeError("Aucun warehouse")
    return rows[0]["id"]


def get_location_id(complete_name: str) -> int:
    rows = search_read("stock.location", [("complete_name", "=", complete_name)], ["id"])
    if not rows:
        raise RuntimeError(f"Location {complete_name} introuvable")
    return rows[0]["id"]


def upsert_rule(product_id: int, location_id: int, warehouse_id: int, min_qty: float, max_qty: float, label: str):
    existing = search_read("stock.warehouse.orderpoint", [
        ("product_id", "=", product_id),
        ("location_id", "=", location_id),
    ], ["id"])
    values = {
        "product_id": product_id,
        "location_id": location_id,
        "warehouse_id": warehouse_id,
        "product_min_qty": min_qty,
        "product_max_qty": max_qty,
        "qty_multiple": 1,
    }
    if existing:
        write("stock.warehouse.orderpoint", [existing[0]["id"]], values)
        print(f"  [UPDATE] {label} (rule_id={existing[0]['id']})")
        return "updated"
    new_id = create("stock.warehouse.orderpoint", values)
    print(f"  [CREATE] {label} (rule_id={new_id})")
    return "created"


def main():
    warehouse_id = get_warehouse_id()
    bulk_loc = get_location_id("MYVO/Stock/Bulk")
    pack_loc = get_location_id("MYVO/Stock/Packaging")
    stats = {"created": 0, "updated": 0, "missing": 0}

    print("=== Bulks ===")
    for r in csv.DictReader(BULK_CSV.open(encoding="utf-8")):
        sku = r["bulk_sku"].strip()
        pid = get_product_id(sku)
        if not pid:
            print(f"  [MISSING] {sku} introuvable")
            stats["missing"] += 1
            continue
        outcome = upsert_rule(pid, bulk_loc, warehouse_id,
                              float(r["min_qty_kg"]), float(r["max_qty_kg"]), sku)
        stats[outcome] += 1

    print("\n=== Packaging ===")
    for r in csv.DictReader(PACK_CSV.open(encoding="utf-8")):
        sku = r["sku"].strip()
        pid = get_product_id(sku)
        if not pid:
            print(f"  [MISSING] {sku} introuvable")
            stats["missing"] += 1
            continue
        outcome = upsert_rule(pid, pack_loc, warehouse_id,
                              float(r["min_qty"]), float(r["max_qty"]), sku)
        stats[outcome] += 1

    print(f"\nDone. Created: {stats['created']}, Updated: {stats['updated']}, Missing: {stats['missing']}")


if __name__ == "__main__":
    main()
