"""Creation des produits packaging dans product.template.

Lit data/packaging_products.csv. Idempotent : match par default_code (SKU).
Pas de tracking lot. UoM 'Units'. Route Buy + seller_ids vers fournisseur packaging.

Odoo 18 storable: type='consu' + tracking='none' (le type 'product' n'existe plus).
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create

CSV_PATH = Path(__file__).parent / "data" / "packaging_products.csv"

ROUTE_BUY_ID = 12

CATEGORY_NAME = "Packaging"


def get_or_create_category() -> int:
    existing = search_read("product.category", [("name", "=", CATEGORY_NAME)], ["id"])
    return existing[0]["id"] if existing else create("product.category", {"name": CATEGORY_NAME})


def get_uom_units() -> int:
    # Try several common labels (depends on Odoo locale)
    for label in ["Units", "Unit(s)", "Unités", "Unite"]:
        rows = search_read("uom.uom", [("name", "=", label)], ["id", "name"])
        if rows:
            return rows[0]["id"]
    raise RuntimeError("UoM 'Units' introuvable - probe avec: search_read('uom.uom', [('category_id.name','=','Unit')], ['id','name'])")


def get_vendor_by_code(code: str) -> int | None:
    rows = search_read("res.partner", [("ref", "=", code)], ["id"])
    return rows[0]["id"] if rows else None


def main():
    category_id = get_or_create_category()
    uom_units_id = get_uom_units()
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, skipped, missing_vendor = 0, 0, 0

    for r in rows:
        sku = r["sku"].strip()
        existing = search_read("product.template", [("default_code", "=", sku)], ["id"])
        if existing:
            print(f"  [SKIP] {sku} (id={existing[0]['id']})")
            skipped += 1
            continue

        vendor_id = get_vendor_by_code(r["vendor_code"].strip())
        if not vendor_id:
            print(f"  [WARN] {sku}: vendor code '{r['vendor_code']}' introuvable")
            missing_vendor += 1

        values = {
            "name": r["name"].strip(),
            "default_code": sku,
            "type": "consu",  # Odoo 18 storable
            "categ_id": category_id,
            "uom_id": uom_units_id,
            "uom_po_id": uom_units_id,
            "tracking": "none",
            "route_ids": [(6, 0, [ROUTE_BUY_ID])],
            "sale_ok": sku == "POMPE-1000",  # seule la pompe 1000ml est aussi vendue
            "purchase_ok": True,
        }
        new_id = create("product.template", values)

        if vendor_id:
            execute("product.supplierinfo", "create", [{
                "partner_id": vendor_id,
                "product_tmpl_id": new_id,
                "delay": 14,
            }])

        print(f"  [CREATE] {sku} -> {values['name']} (id={new_id})")
        created += 1

    print(f"\nDone. Created: {created}, Skipped: {skipped}, Missing vendor: {missing_vendor}")


if __name__ == "__main__":
    main()
