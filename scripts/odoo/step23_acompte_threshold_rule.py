"""Automated rule: set sale.order.prepayment_percent based on amount_total.

Logic:
  - amount_total <  1000 € → prepayment_percent = 1.0  (100% upfront)
  - amount_total >= 1000 € → prepayment_percent = 0.5  (50% acompte)

The rule fires on create + write of sale.order in DRAFT or SENT state only,
so confirmed orders (state='sale') are never re-touched.

Idempotent: looks up by external xml_id, updates code if rule exists.

Run: python step04_acompte_threshold_rule.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, execute, write

THRESHOLD_EUR = 1000
PCT_BELOW = 1.0   # 100%
PCT_ABOVE = 0.5   # 50%

RULE_NAME = "MyLab — Acompte conditionnel selon montant devis"

# Find sale.order model id
sale_model = search_read("ir.model", [("model", "=", "sale.order")], ["id"])
if not sale_model:
    print("ERROR: sale.order model not found")
    sys.exit(1)
sale_model_id = sale_model[0]["id"]

# Find the amount_total field id (used as trigger field)
amount_field = search_read(
    "ir.model.fields",
    [("model", "=", "sale.order"), ("name", "=", "amount_total")],
    ["id"],
)
amount_field_id = amount_field[0]["id"]

# Server action code (Python, runs in Odoo env with `record` as the current sale.order)
SERVER_CODE = f"""# MyLab acompte conditionnel
# Skip already-confirmed orders to avoid touching closed deals
if record.state in ('draft', 'sent'):
    threshold = {THRESHOLD_EUR}
    new_pct = {PCT_BELOW} if record.amount_total < threshold else {PCT_ABOVE}
    if record.prepayment_percent != new_pct:
        record.write({{'prepayment_percent': new_pct}})
"""

# Check if rule already exists
existing = search_read(
    "base.automation",
    [("name", "=", RULE_NAME)],
    ["id", "active", "action_server_ids"],
)

if existing:
    rule = existing[0]
    print(f"✓ Rule already exists: id={rule['id']}, active={rule['active']}")
    # Update the server action code in case logic changed
    if rule["action_server_ids"]:
        srv_id = rule["action_server_ids"][0]
        write("ir.actions.server", [srv_id], {"code": SERVER_CODE})
        print(f"  Updated server action code (id={srv_id})")
    sys.exit(0)

# Create the server action
srv_values = {
    "name": f"{RULE_NAME} — Action",
    "model_id": sale_model_id,
    "state": "code",
    "code": SERVER_CODE,
}
srv_id = create("ir.actions.server", srv_values)
print(f"Created server action: id={srv_id}")

# Create the automation rule
auto_values = {
    "name": RULE_NAME,
    "model_id": sale_model_id,
    "trigger": "on_create_or_write",
    "trigger_field_ids": [(6, 0, [amount_field_id])],
    "filter_domain": "[('state', 'in', ['draft', 'sent'])]",
    "action_server_ids": [(6, 0, [srv_id])],
    "active": True,
}
auto_id = create("base.automation", auto_values)
print(f"✓ Automation rule created: id={auto_id}")
print()
print(f"Rule: amount < {THRESHOLD_EUR}€ → prepayment_percent = {PCT_BELOW * 100:.0f}%")
print(f"      amount ≥ {THRESHOLD_EUR}€ → prepayment_percent = {PCT_ABOVE * 100:.0f}%")
print(f"Triggers: on create + write of sale.order in state draft/sent")
