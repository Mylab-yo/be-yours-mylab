"""Create custom field x_carton_capacity on product.template.

Idempotent: if the field already exists, does nothing.
"""
from scripts.odoo._client import execute, search, create

FIELD_NAME = "x_carton_capacity"
MODEL_NAME = "product.template"


def main():
    # Find model id
    model_ids = search("ir.model", [("model", "=", MODEL_NAME)])
    if not model_ids:
        raise RuntimeError(f"Model {MODEL_NAME} not found")
    model_id = model_ids[0]

    # Check if field already exists
    existing = search("ir.model.fields",
                      [("model", "=", MODEL_NAME), ("name", "=", FIELD_NAME)])
    if existing:
        print(f"Field {FIELD_NAME} already exists (id={existing[0]}), skipping")
        return

    # Create field
    field_id = create("ir.model.fields", {
        "name": FIELD_NAME,
        "field_description": "Capacité carton (unités)",
        "model_id": model_id,
        "ttype": "integer",
        "help": "Nombre d'unités par carton d'expédition. 0 = pas de carton défini.",
    })
    print(f"Created field {FIELD_NAME} (id={field_id}) on {MODEL_NAME}")


if __name__ == "__main__":
    main()
