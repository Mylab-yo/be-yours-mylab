"""Création du fournisseur principal Laboratoires FP Cosmetics dans res.partner.

Idempotent : match par ref='FP-COSM'.
"""
from scripts.odoo._client import execute, search_read, create, write


def get_country_id(code: str = "FR") -> int:
    rows = search_read("res.country", [("code", "=", code)], ["id"])
    if not rows:
        raise RuntimeError(f"Pays code={code} introuvable dans res.country")
    return rows[0]["id"]


def main():
    country_id = get_country_id("FR")
    values = {
        "name": "Laboratoires FP Cosmetics",
        "ref": "FP-COSM",
        "street": "396 ZI Le Colombier",
        "street2": "BP 35",
        "zip": "01330",
        "city": "VILLARS LES DOMBES",
        "country_id": country_id,
        "phone": "04 78 55 90 68",
        "mobile": "04 78 55 55 99",
        "email": "c.moreau@favre-cosmetics.com",
        "website": "www.favre-cosmetics.com",
        "is_company": True,
        "supplier_rank": 1,
        "comment": "Façonnier cosmétique principal MyLab — coordonne la production des shampoings, crèmes, masques, après-shampoings.",
    }

    existing = search_read("res.partner", [("ref", "=", "FP-COSM")], ["id", "name"])
    if existing:
        partner_id = existing[0]["id"]
        write("res.partner", [partner_id], values)
        print(f"  [UPDATE] FP-COSM partner_id={partner_id} name={values['name']}")
    else:
        new_id = create("res.partner", values)
        print(f"  [CREATE] FP-COSM partner_id={new_id} name={values['name']}")
        partner_id = new_id

    # Verify
    final = search_read("res.partner", [("id", "=", partner_id)], ["name", "email", "city", "supplier_rank"])
    print(f"\nVerification : {final[0]}")


if __name__ == "__main__":
    main()
