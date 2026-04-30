"""Create the custom fields used to track follow-up state on devis and factures.

Adds:
  - sale.order.x_followup_level   (integer, 0 = none, 1/2/3 = sent levels)
  - sale.order.x_followup_last_sent_date (date)
  - account.move.x_followup_level (integer, same)
  - account.move.x_followup_last_sent_date (date)

Idempotent: skips fields that already exist.

Run: python step32_create_followup_fields.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create

FIELDS = [
    ("sale.order", "x_followup_level", "integer",
     "Niveau de relance envoyé (0=aucune, 1=L1 doux, 2=L2 direct, 3=L3 expiré)"),
    ("sale.order", "x_followup_last_sent_date", "date",
     "Dernière date d'envoi d'une relance"),
    ("account.move", "x_followup_level", "integer",
     "Niveau de relance envoyé (0=aucune, 1=L1 courtois, 2=L2 ferme, 3=L3 mise en demeure)"),
    ("account.move", "x_followup_last_sent_date", "date",
     "Dernière date d'envoi d'une relance"),
]

for model_name, field_name, ttype, label in FIELDS:
    # Get model id
    model = search_read("ir.model", [("model", "=", model_name)], ["id"])
    if not model:
        print(f"⚠ Model {model_name} not found — skipping")
        continue
    model_id = model[0]["id"]

    # Skip if exists
    existing = search_read("ir.model.fields",
                           [("model", "=", model_name), ("name", "=", field_name)],
                           ["id"])
    if existing:
        print(f"✓ {model_name}.{field_name} already exists (id={existing[0]['id']})")
        continue

    new_id = create("ir.model.fields", {
        "name": field_name,
        "field_description": label,
        "model_id": model_id,
        "ttype": ttype,
        "state": "manual",  # Studio-style custom field
        "store": True,
    })
    print(f"✓ Created {model_name}.{field_name} (id={new_id}, type={ttype})")
