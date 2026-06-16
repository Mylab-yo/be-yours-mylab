"""Deploy auto-palette rule: if sale.order shipping_weight > 200kg, set carrier to palette.

Idempotent:
- Updates carrier id=19 (clears country_ids, renames)
- Creates or updates base.automation + ir.actions.server
"""
from scripts.odoo._client import execute, search, search_read, create, write

PALETTE_CARRIER_ID = 19
THRESHOLD_KG = 200
AUTOMATION_NAME = "MyLab - Auto palette si poids > 200kg"
ACTION_NAME = "MyLab - Auto palette: set carrier_id"

# ---------------------------------------------------------------------------
# Step 1: Update carrier — drop country restriction, rename
# ---------------------------------------------------------------------------
print("=== Step 1: Update carrier id=19 (Envoi Palette) ===")

# Collect EU countries from DPD Euro 1-5
eu_carriers = search_read(
    "delivery.carrier",
    [("id", "in", [14, 15, 16, 17, 18])],
    ["id", "name", "country_ids"],
)
eu_country_ids = set()
for c in eu_carriers:
    eu_country_ids.update(c["country_ids"])
    print(f"  DPD {c['name'][:50]} -> {len(c['country_ids'])} countries")

# Add France too (always include FR)
fr = search("res.country", [("code", "=", "FR")], limit=1)
all_country_ids = list(eu_country_ids | set(fr))
print(f"  Total countries on palette: {len(all_country_ids)}")

write("delivery.carrier", [PALETTE_CARRIER_ID], {
    "name": "Envoi Palette",
    "country_ids": [(6, 0, all_country_ids)],
})
upd = search_read("delivery.carrier", [("id", "=", PALETTE_CARRIER_ID)],
                  ["name", "country_ids", "active"])[0]
print(f"  -> name={upd['name']!r}, active={upd['active']}, countries={len(upd['country_ids'])}")

# ---------------------------------------------------------------------------
# Step 2: Get sale.order model id + relevant field id (shipping_weight)
# ---------------------------------------------------------------------------
print("\n=== Step 2: Resolve model + trigger field ids ===")
so_model = search("ir.model", [("model", "=", "sale.order")], limit=1)
if not so_model:
    raise RuntimeError("sale.order model not found")
so_model_id = so_model[0]
print(f"  sale.order model_id = {so_model_id}")

# Trigger field: shipping_weight (computed/stored). If not stored, fallback to order_line.
sw_fields = search_read(
    "ir.model.fields",
    [("model_id", "=", so_model_id), ("name", "in", ["shipping_weight", "order_line"])],
    ["id", "name", "store", "compute"],
)
field_id_map = {f["name"]: f for f in sw_fields}
print(f"  shipping_weight: {field_id_map.get('shipping_weight')}")
print(f"  order_line:      {field_id_map.get('order_line')}")

# We trigger on order_line change (which recomputes shipping_weight).
# This is more reliable than triggering on the computed field itself.
trigger_field_ids = [field_id_map["order_line"]["id"]]
if field_id_map.get("shipping_weight", {}).get("store"):
    trigger_field_ids.append(field_id_map["shipping_weight"]["id"])

# ---------------------------------------------------------------------------
# Step 3: Create or update base.automation
# ---------------------------------------------------------------------------
print("\n=== Step 3: base.automation rule ===")
existing = search("base.automation", [("name", "=", AUTOMATION_NAME)])
filter_domain = (
    f"[('shipping_weight', '>', {THRESHOLD_KG}), "
    f"('carrier_id', '!=', {PALETTE_CARRIER_ID}), "
    f"('state', 'in', ['draft', 'sent'])]"
)

automation_values = {
    "name": AUTOMATION_NAME,
    "model_id": so_model_id,
    "trigger": "on_create_or_write",
    "filter_domain": filter_domain,
    "trigger_field_ids": [(6, 0, trigger_field_ids)],
    "active": True,
}

if existing:
    automation_id = existing[0]
    write("base.automation", [automation_id], automation_values)
    print(f"  Updated automation id={automation_id}")
else:
    automation_id = create("base.automation", automation_values)
    print(f"  Created automation id={automation_id}")

# ---------------------------------------------------------------------------
# Step 4: Create or update ir.actions.server linked to automation
# ---------------------------------------------------------------------------
print("\n=== Step 4: ir.actions.server with code ===")

code = f"""# MyLab - Auto palette si poids > {THRESHOLD_KG}kg
# Triggered when sale.order shipping_weight exceeds {THRESHOLD_KG}kg (draft/sent quotes only)
PALETTE_ID = {PALETTE_CARRIER_ID}
for rec in records:
    if rec.shipping_weight > {THRESHOLD_KG} and rec.carrier_id.id != PALETTE_ID:
        rec.write({{'carrier_id': PALETTE_ID, 'recompute_delivery_price': True}})
        rec.message_post(body='Carrier bascule automatiquement sur Envoi Palette '
                              '(poids du devis > {THRESHOLD_KG}kg).')
"""

existing_action = search("ir.actions.server",
                         [("base_automation_id", "=", automation_id)])

action_values = {
    "name": ACTION_NAME,
    "model_id": so_model_id,
    "state": "code",
    "code": code,
    "base_automation_id": automation_id,
    "usage": "base_automation",
}

if existing_action:
    action_id = existing_action[0]
    write("ir.actions.server", [action_id], action_values)
    print(f"  Updated server action id={action_id}")
else:
    action_id = create("ir.actions.server", action_values)
    print(f"  Created server action id={action_id}")

# ---------------------------------------------------------------------------
# Step 5: Verify final state
# ---------------------------------------------------------------------------
print("\n=== Step 5: Verify ===")
aut = search_read("base.automation", [("id", "=", automation_id)],
                  ["name", "active", "trigger", "filter_domain", "action_server_ids"])[0]
print(f"  automation: {aut['name']}")
print(f"    active={aut['active']}, trigger={aut['trigger']}")
print(f"    domain={aut['filter_domain']}")
print(f"    action_server_ids={aut['action_server_ids']}")

# Quick simulation: count current draft/sent SO that would match
matching = search("sale.order", [
    ("shipping_weight", ">", THRESHOLD_KG),
    ("carrier_id", "!=", PALETTE_CARRIER_ID),
    ("state", "in", ["draft", "sent"]),
])
print(f"\n  Existing draft/sent quotes > {THRESHOLD_KG}kg NOT on palette: {len(matching)}")
if matching:
    sample = search_read("sale.order", [("id", "in", matching[:5])],
                         ["name", "shipping_weight", "carrier_id"])
    for s in sample:
        c = s["carrier_id"][1] if s["carrier_id"] else "-"
        print(f"    {s['name']}: weight={s['shipping_weight']}kg, current carrier={c}")
    print("  (These existing quotes will be auto-switched when next modified.)")
