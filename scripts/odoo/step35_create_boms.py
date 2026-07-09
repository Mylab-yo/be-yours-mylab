"""Création des nomenclatures (BoMs) pour les produits finis qui consomment du bulk.

Lit data/finished_to_components.csv. Idempotent : si une BoM existe deja pour
un produit fini, elle est mise a jour (lignes recalculees). Sinon creee.

Populate aussi le champ x_mylab_bom_summary (JSON) sur le produit fini, utilise
par le workflow n8n de sync stock Shopify.
"""
import csv
import json
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write, search

CSV_PATH = Path(__file__).parent / "data" / "finished_to_components.csv"


def get_product_id_by_sku(sku: str) -> int | None:
    """Retourne le product.product (variant) id pour ce SKU.
    Pour un produit sans variants, c'est le seul variant du template."""
    if not sku:
        return None
    rows = search_read("product.product", [("default_code", "=", sku)], ["id", "product_tmpl_id"])
    return rows[0]["id"] if rows else None


def get_template_id_by_sku(sku: str) -> int | None:
    rows = search_read("product.template", [("default_code", "=", sku)], ["id"])
    return rows[0]["id"] if rows else None


def main():
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, updated, skipped, missing = 0, 0, 0, 0

    for r in rows:
        finished_sku = r["finished_sku"].strip()
        bulk_sku = r["bulk_sku"].strip()
        flacon_sku = r["flacon_sku"].strip()
        bouchon_sku = r["bouchon_sku"].strip()
        bulk_kg = float(r["bulk_qty_kg"])

        if not (flacon_sku and bouchon_sku):
            print(f"  [SKIP-EMPTY] {finished_sku} (composants manquants dans CSV)")
            skipped += 1
            continue

        # Récupérer les IDs produits
        finished_tmpl_id = get_template_id_by_sku(finished_sku)
        finished_product_id = get_product_id_by_sku(finished_sku)
        bulk_id = get_product_id_by_sku(bulk_sku)
        flacon_id = get_product_id_by_sku(flacon_sku)
        bouchon_id = get_product_id_by_sku(bouchon_sku)

        if not all([finished_tmpl_id, finished_product_id, bulk_id, flacon_id, bouchon_id]):
            details = {
                "finished": finished_tmpl_id,
                "bulk": bulk_id,
                "flacon": flacon_id,
                "bouchon": bouchon_id,
            }
            print(f"  [MISSING] {finished_sku}: produit introuvable {details}")
            missing += 1
            continue

        # Vérifier si BoM existe
        bom_existing = search_read("mrp.bom", [("product_tmpl_id", "=", finished_tmpl_id)], ["id"])

        bom_lines = [
            (0, 0, {"product_id": bulk_id, "product_qty": bulk_kg}),
            (0, 0, {"product_id": flacon_id, "product_qty": 1}),
            (0, 0, {"product_id": bouchon_id, "product_qty": 1}),
        ]

        if bom_existing:
            # Update : recréer les lignes
            bom_id = bom_existing[0]["id"]
            # Supprimer les anciennes lignes
            old_line_ids = search("mrp.bom.line", [("bom_id", "=", bom_id)])
            if old_line_ids:
                execute("mrp.bom.line", "unlink", [old_line_ids])
            # Recreer
            write("mrp.bom", [bom_id], {"bom_line_ids": bom_lines})
            print(f"  [UPDATE] BoM pour {finished_sku} (id={bom_id})")
            updated += 1
        else:
            bom_id = create("mrp.bom", {
                "product_tmpl_id": finished_tmpl_id,
                "product_qty": 1,
                "type": "normal",
                "bom_line_ids": bom_lines,
            })
            print(f"  [CREATE] BoM pour {finished_sku} (bom_id={bom_id})")
            created += 1

        # Populer x_mylab_bom_summary
        summary = json.dumps({
            "bulk_sku": bulk_sku,
            "bulk_kg": bulk_kg,
            "flacon_sku": flacon_sku,
            "bouchon_sku": bouchon_sku,
            "family": r["family"].strip(),
            "contenance": r["contenance"].strip(),
        })
        write("product.template", [finished_tmpl_id], {"x_mylab_bom_summary": summary})

    print(f"\nDone. Created: {created}, Updated: {updated}, Skipped: {skipped}, Missing: {missing}")


if __name__ == "__main__":
    main()
