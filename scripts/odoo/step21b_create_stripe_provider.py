"""Create the Stripe payment.provider record manually.

In Odoo 18, installing payment_stripe does NOT auto-create the provider record
(behavior changed from v17). Create it manually with state=disabled — user
pastes API keys + flips state=enabled in the UI.

Idempotent: skips if a stripe provider already exists.

Run AFTER step21 has installed the payment_stripe module.
Run: python step21b_create_stripe_provider.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create

existing = search_read(
    "payment.provider",
    [("code", "=", "stripe")],
    ["id", "name", "state"],
)
if existing:
    p = existing[0]
    print(f"✓ Stripe provider already exists: [{p['id']}] {p['name']} (state={p['state']})")
    sys.exit(0)

# Verify payment_stripe module is installed
mod = search_read("ir.module.module",
                  [("name", "=", "payment_stripe")],
                  ["state"])
if not mod or mod[0]["state"] != "installed":
    print("ERROR: payment_stripe module is not installed. Run step21 first.")
    sys.exit(1)

companies = search_read("res.company", [], ["id"])
company_id = companies[0]["id"]

values = {
    "name": "Stripe",
    "code": "stripe",
    "state": "disabled",  # User flips to 'enabled' or 'test' after pasting keys
    "company_id": company_id,
}

new_id = create("payment.provider", values)
print(f"✓ Stripe provider created: id={new_id}, state=disabled")
print(f"  → UI: Settings → Payment Providers → Stripe")
print(f"  → Onglet Credentials : coller pk_live_... + sk_live_...")
print(f"  → Puis State = Enabled")
