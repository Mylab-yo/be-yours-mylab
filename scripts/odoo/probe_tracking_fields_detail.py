"""Detail des champs tracking : readonly/store/compute + valeur tracking_url des carriers DPD."""
from scripts.odoo._client import search_read, execute

print("stock.picking - attributs des champs tracking :")
fg = execute("stock.picking", "fields_get",
    [["carrier_tracking_ref", "carrier_tracking_url"]],
    {"attributes": ["string", "type", "readonly", "store", "required"]})
for f, m in fg.items():
    print(f"  {f}: {m}")

print("\ndelivery.carrier - champ tracking_url (template lien) :")
fg2 = execute("delivery.carrier", "fields_get", [["tracking_url"]],
    {"attributes": ["string", "type", "help"]})
print("  meta:", fg2)
carriers = search_read("delivery.carrier", [("delivery_type", "=", "base_on_rule")],
    ["id", "name", "tracking_url"], limit=20)
for c in carriers:
    print(f"  id={c['id']} tracking_url={c.get('tracking_url')!r}  {c['name']}")
