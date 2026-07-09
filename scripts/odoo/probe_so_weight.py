"""Check how SO weight is computed + automation infra."""
from scripts.odoo._client import execute, search_read

# Weight-related fields on sale.order
print("=== sale.order fields (weight/shipping/carrier) ===")
fields = execute("sale.order", "fields_get", [], {"attributes": ["string", "type"]})
for fname in sorted(fields):
    if any(k in fname.lower() for k in ("weight", "carrier", "shipping", "delivery")):
        print(f"  {fname}: {fields[fname]['type']} - {fields[fname]['string']}")

# Sample SO with palette already used
print("\n=== S00458 (used palette) details ===")
sos = search_read("sale.order", [("name", "=", "S00458")],
                  ["id", "name", "carrier_id", "amount_total", "order_line"])
if sos:
    so = sos[0]
    print(f"  {so}")
    # Check order lines weight
    lines = search_read("sale.order.line", [("order_id", "=", so["id"])],
                        ["id", "name", "product_id", "product_uom_qty"])
    total_w = 0
    for line in lines:
        if line["product_id"]:
            p = search_read("product.product", [("id", "=", line["product_id"][0])],
                            ["id", "weight", "name"])
            if p:
                w = p[0]["weight"] * line["product_uom_qty"]
                total_w += w
                print(f"    line {line['name'][:40]:40s} qty={line['product_uom_qty']} weight_unit={p[0]['weight']} total={w}")
    print(f"  TOTAL weight: {total_w} kg")

# Check existing automation rules (base_automation)
print("\n=== base.automation rules ===")
try:
    rules = search_read("base.automation", [], ["id", "name", "model_id", "active", "trigger"])
    for r in rules:
        print(f"  id={r['id']} | active={r['active']} | model={r['model_id'][1] if r['model_id'] else '-'} | "
              f"trigger={r['trigger']!r} | {r['name']!r}")
except Exception as e:
    print(f"  err: {e}")

# Modules available
print("\n=== Module 'base_automation' state ===")
mods = search_read("ir.module.module", [("name", "in", ["base_automation", "delivery"])],
                   ["name", "state"])
for m in mods:
    print(f"  {m['name']}: {m['state']}")
