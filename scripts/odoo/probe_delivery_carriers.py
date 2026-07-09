"""Probe Odoo delivery carriers to plan the palette rule."""
from scripts.odoo._client import search_read, execute

print("=== All delivery.carrier records ===")
carriers = search_read(
    "delivery.carrier",
    [],
    ["id", "name", "delivery_type", "active", "country_ids",
     "max_weight", "fixed_price", "free_over"],
)
for c in carriers:
    print(f"  id={c['id']:3d} | active={c['active']} | {c['name']!r:50s} | "
          f"type={c['delivery_type']!r:20s} | max_weight={c['max_weight']} | "
          f"countries={len(c['country_ids'])}")

# Check if there are extra fields about weight/palette
print("\n=== delivery.carrier fields (filter: weight/palette/rule) ===")
fields = execute("delivery.carrier", "fields_get", [], {"attributes": ["string", "type"]})
for fname, finfo in sorted(fields.items()):
    if any(k in fname.lower() for k in ("weight", "palette", "rule", "max")):
        print(f"  {fname}: {finfo['type']} — {finfo['string']}")

# Sample sale order to see how carrier_id works
print("\n=== Recent sale.order with carrier_id set ===")
sos = search_read(
    "sale.order",
    [("carrier_id", "!=", False), ("state", "in", ["sale", "done"])],
    ["id", "name", "carrier_id", "amount_total"],
    limit=5,
)
for so in sos:
    print(f"  {so['name']}: carrier={so['carrier_id']}, amount={so['amount_total']}")

# Existing automations / server actions on sale.order
print("\n=== ir.actions.server on sale.order ===")
actions = search_read(
    "ir.actions.server",
    [("model_id.model", "=", "sale.order")],
    ["id", "name", "state", "binding_model_id", "code"],
)
for a in actions:
    code_preview = (a.get("code") or "")[:80].replace("\n", " ")
    print(f"  id={a['id']} | {a['name']!r}: state={a['state']}, code={code_preview!r}")
