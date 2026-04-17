"""Ensure 'Intracommunautaire' and 'Export' fiscal positions exist in Odoo for company 3.

Idempotent: if they already exist, prints their ids and exits without changes.
"""
from scripts.odoo._client import search_read, create

COMPANY_ID = 3  # SARL STARTEC

POSITIONS = [
    {
        "name": "Intracommunautaire (0%)",
        "note": "Livraison intracommunautaire B2B avec numéro de TVA valide — exonération TVA art. 262 ter I du CGI",
        "auto_apply": False,
        "vat_required": True,
    },
    {
        "name": "Export (0%)",
        "note": "Export hors Union Européenne — exonération TVA art. 262 I du CGI",
        "auto_apply": False,
        "vat_required": False,
    },
]


def main():
    for fp in POSITIONS:
        existing = search_read(
            "account.fiscal.position",
            [("name", "=", fp["name"]), ("company_id", "=", COMPANY_ID)],
            ["id", "name"],
            limit=1,
        )
        if existing:
            print(f"Fiscal position '{fp['name']}' exists (id={existing[0]['id']}), skipping")
            continue
        new_id = create("account.fiscal.position", {
            "name": fp["name"],
            "note": fp["note"],
            "auto_apply": fp["auto_apply"],
            "vat_required": fp["vat_required"],
            "company_id": COMPANY_ID,
        })
        print(f"Created fiscal position '{fp['name']}' (id={new_id})")


if __name__ == "__main__":
    main()
