"""Création des fournisseurs packaging dans res.partner.

Lit data/packaging_vendors.csv. Idempotent : match par 'ref' (vendor_code stocké en réf interne).
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write

CSV_PATH = Path(__file__).parent / "data" / "packaging_vendors.csv"


def main():
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, skipped, updated = 0, 0, 0
    for r in rows:
        code = r["vendor_code"].strip()
        existing = search_read("res.partner", [("ref", "=", code)], ["id", "name", "email"])
        values = {
            "name": r["vendor_name"].strip(),
            "email": r["email"].strip(),
            "phone": r.get("phone", "").strip(),
            "ref": code,
            "is_company": True,
            "supplier_rank": 1,
            "comment": r.get("notes", "").strip(),
        }
        if existing:
            partner_id = existing[0]["id"]
            # Mettre à jour si nom ou email a changé
            if existing[0]["name"] != values["name"] or existing[0]["email"] != values["email"]:
                write("res.partner", [partner_id], values)
                print(f"  [UPDATE] {code} -> {values['name']} (id={partner_id})")
                updated += 1
            else:
                print(f"  [SKIP] {code} (id={partner_id})")
                skipped += 1
            continue
        new_id = create("res.partner", values)
        print(f"  [CREATE] {code} -> {values['name']} (id={new_id})")
        created += 1
    print(f"\nDone. Created: {created}, Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
