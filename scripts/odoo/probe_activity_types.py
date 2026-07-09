"""Lister les activity types existants pour decider si on en cree un nouveau."""
from scripts.odoo._client import search_read

acts = search_read("mail.activity.type", [], ["id", "name", "res_model", "summary"], limit=30)
print("=== Activity types existants ===")
for a in acts:
    print(f"  [{a['id']:3d}] {a['name']!r:40s} res_model={a.get('res_model')!r}  summary={a.get('summary')!r}")

# Find existing actions related to mandat / dossier cosmeto
print("\n=== Server actions existantes pertinentes ===")
actions = search_read(
    "ir.actions.server",
    ["|", ("name", "ilike", "mandat"), ("name", "ilike", "dossier")],
    ["id", "name", "model_id", "state", "binding_model_id"],
)
for a in actions:
    print(f"  [{a['id']:3d}] {a['name']!r} model={a['model_id']} state={a['state']}")
