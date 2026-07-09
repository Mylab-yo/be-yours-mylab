"""Cree le champ custom x_mandat_sent_at (Datetime) sur account.move.

Marqueur d'idempotence pour l'envoi automatique du mandat de representation :
tamponne a chaque envoi reussi (auto ou manuel) => jamais de double envoi.

Idempotent : si le champ existe deja, ne fait rien.

Run : python -m scripts.odoo.setup_mandat_field
"""
import sys
from scripts.odoo._client import search_read, create

FIELD_NAME = "x_mandat_sent_at"
MODEL = "account.move"

# ir.model id de account.move
model_rows = search_read("ir.model", [("model", "=", MODEL)], ["id"])
if not model_rows:
    print(f"ERREUR : modele {MODEL} introuvable")
    sys.exit(1)
model_id = model_rows[0]["id"]

existing = search_read(
    "ir.model.fields",
    [("model", "=", MODEL), ("name", "=", FIELD_NAME)],
    ["id", "ttype", "field_description"],
)
if existing:
    f = existing[0]
    print(f"OK champ deja present : id={f['id']} ttype={f['ttype']} desc={f['field_description']!r}")
    sys.exit(0)

field_id = create("ir.model.fields", {
    "name": FIELD_NAME,
    "model": MODEL,
    "model_id": model_id,
    "field_description": "Mandat envoye le",
    "ttype": "datetime",
    "state": "manual",
    "help": "Date d'envoi du mandat de Personne Responsable. Tamponne par "
            "auto_send_mandats / send_mandat_representation. Vide = pas encore envoye.",
})
print(f"+ champ cree : ir.model.fields id={field_id} ({MODEL}.{FIELD_NAME}, datetime)")
