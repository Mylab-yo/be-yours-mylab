"""Création du champ custom x_mylab_bom_summary sur product.template.

Champ Text (stocke un JSON). Utilisé par le workflow n8n de sync stock Shopify
pour calculer le stock projeté sans avoir à re-parser la BoM Odoo à chaque sync.

Idempotent : skip si le champ existe déjà.
"""
from scripts.odoo._client import execute, search_read, create

FIELD_NAME = "x_mylab_bom_summary"
FIELD_MODEL = "product.template"
FIELD_LABEL = "MyLab BoM Summary (JSON)"


def main():
    model_rows = search_read("ir.model", [("model", "=", FIELD_MODEL)], ["id"])
    if not model_rows:
        raise RuntimeError(f"Model {FIELD_MODEL} introuvable")
    model_id = model_rows[0]["id"]

    existing = search_read("ir.model.fields", [
        ("model", "=", FIELD_MODEL),
        ("name", "=", FIELD_NAME),
    ], ["id", "name", "ttype"])
    if existing:
        print(f"  [SKIP] {FIELD_NAME} existe déjà (id={existing[0]['id']}, type={existing[0]['ttype']})")
        return

    new_id = create("ir.model.fields", {
        "name": FIELD_NAME,
        "field_description": FIELD_LABEL,
        "model_id": model_id,
        "model": FIELD_MODEL,
        "ttype": "text",
        "state": "manual",  # champ custom (pas issu d'un module)
        "store": True,
        "copied": False,
    })
    print(f"  [CREATE] {FIELD_NAME} sur {FIELD_MODEL} (id={new_id})")
    print("\nDone.")


if __name__ == "__main__":
    main()
