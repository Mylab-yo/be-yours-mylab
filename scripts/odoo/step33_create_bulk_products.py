"""Creation des produits bulk dans product.template.

Lit data/bulk_formulas.csv. Idempotent : match par default_code (SKU).
Tracking by lot. Unite kg. Routes Buy (id=12) ou Manufacture (id=13) selon CSV.
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create

CSV_PATH = Path(__file__).parent / "data" / "bulk_formulas.csv"

ROUTE_BUY_ID = 12
ROUTE_MANUFACTURE_ID = 13

CATEGORY_NAME = "Matieres premieres / Bulk"  # plain ASCII to avoid Windows console encoding issues in prints


def get_or_create_category() -> int:
    existing = search_read("product.category", [("name", "=", CATEGORY_NAME)], ["id"])
    if existing:
        return existing[0]["id"]
    return create("product.category", {"name": CATEGORY_NAME})


def get_uom_kg() -> int:
    rows = search_read("uom.uom", [("name", "=", "kg")], ["id"])
    if not rows:
        raise RuntimeError("UoM 'kg' introuvable")
    return rows[0]["id"]


def get_vendor_id(name: str) -> int | None:
    """Find vendor by exact name first, then ilike fallback for FP Cosmetics variants."""
    if not name:
        return None
    rows = search_read("res.partner", [("name", "=", name), ("supplier_rank", ">", 0)], ["id"])
    if not rows:
        # Fallback for FP Cosmetics (registered as "Laboratoires FP Cosmetics")
        rows = search_read("res.partner", [("name", "ilike", "FP Cosmetics"), ("supplier_rank", ">", 0)], ["id"])
    return rows[0]["id"] if rows else None


def main():
    category_id = get_or_create_category()
    uom_kg_id = get_uom_kg()
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, skipped, missing_vendor = 0, 0, 0

    for r in rows:
        sku = r["bulk_sku"].strip()
        existing = search_read("product.template", [("default_code", "=", sku)], ["id", "name"])
        if existing:
            print(f"  [SKIP] {sku} (id={existing[0]['id']})")
            skipped += 1
            continue

        route_id = ROUTE_BUY_ID if r["route"].strip() == "Buy" else ROUTE_MANUFACTURE_ID
        vendor_name = r["vendor"].strip()
        vendor_id = get_vendor_id(vendor_name)

        if vendor_name and not vendor_id:
            print(f"  [WARN] {sku} : fournisseur '{vendor_name}' introuvable, produit cree sans lien fournisseur")
            missing_vendor += 1

        values = {
            "name": r["bulk_name"].strip(),
            "default_code": sku,
            "type": "consu",  # storable (Odoo 18: 'consu' + tracking = storable behaviour)
            "categ_id": category_id,
            "uom_id": uom_kg_id,
            "uom_po_id": uom_kg_id,
            "tracking": "lot",
            "route_ids": [(6, 0, [route_id])],
            "sale_ok": False,
            "purchase_ok": r["route"].strip() == "Buy",
        }
        new_id = create("product.template", values)

        # Lier le fournisseur si applicable (table product.supplierinfo)
        if vendor_id and r["route"].strip() == "Buy":
            execute("product.supplierinfo", "create", [{
                "partner_id": vendor_id,
                "product_tmpl_id": new_id,
                "delay": 14,  # default 14 jours, a ajuster manuellement par formule
            }])

        print(f"  [CREATE] {sku} -> {values['name']} (id={new_id})")
        created += 1

    print(f"\nDone. Created: {created}, Skipped: {skipped}, Missing vendor: {missing_vendor}")


if __name__ == "__main__":
    main()
