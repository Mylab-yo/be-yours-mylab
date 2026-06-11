"""Genere le template CSV initial_inventory.csv a partir de bulk_formulas + packaging_products.

Le fichier produit est destine a etre rempli MANUELLEMENT par Yoann avec les
quantites physiques actuelles + les numeros de lot des futs bulk en cours.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def main():
    rows = []
    # Bulks -> MYVO/Stock/Bulk
    with (DATA / "bulk_formulas.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "sku": r["bulk_sku"],
                "location": "MYVO/Stock/Bulk",
                "quantity": "",
                "lot_name": "",
                "note": "",
            })
    # Packaging -> MYVO/Stock/Packaging
    with (DATA / "packaging_products.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "sku": r["sku"],
                "location": "MYVO/Stock/Packaging",
                "quantity": "",
                "lot_name": "",
                "note": "",
            })
    # Produits finis (conditionnes) -> MYVO/Stock/Fini (gerent un lot)
    with (DATA / "finished_to_components.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "sku": r["finished_sku"],
                "location": "MYVO/Stock/Fini",
                "quantity": "",
                "lot_name": "",
                "note": "",
            })

    out = DATA / "initial_inventory.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "location", "quantity", "lot_name", "note"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
