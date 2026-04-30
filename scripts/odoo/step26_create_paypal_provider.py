"""Create the PayPal payment.provider record + link the PayPal method.

Module payment_paypal is already installed. We only need to create the
provider record (Odoo 18 doesn't seed it auto) and link the method to
avoid the Owl form crash.

Idempotent: skips if a paypal provider already exists.

Run: python step26_create_paypal_provider.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, write, execute

# 1. Verify module installed
mod = search_read("ir.module.module",
                  [("name", "=", "payment_paypal")],
                  ["state"])
if not mod or mod[0]["state"] != "installed":
    print("ERROR: payment_paypal module not installed. Install via Apps first.")
    sys.exit(1)

# 2. Skip if provider exists
existing = search_read("payment.provider",
                       [("code", "=", "paypal")],
                       ["id", "name", "state"])
if existing:
    p = existing[0]
    print(f"✓ PayPal provider already exists: [{p['id']}] {p['name']} (state={p['state']})")
else:
    companies = search_read("res.company", [], ["id"])
    company_id = companies[0]["id"]

    new_id = create("payment.provider", {
        "name": "PayPal",
        "code": "paypal",
        "state": "disabled",
        "company_id": company_id,
    })
    print(f"✓ PayPal provider created: id={new_id}, state=disabled")
    existing = [{"id": new_id, "payment_method_ids": []}]

# 3. Link PayPal payment method
provider = search_read("payment.provider",
                       [("code", "=", "paypal")],
                       ["id", "payment_method_ids"])[0]

methods = execute("payment.method", "search_read",
                  [[("code", "=", "paypal")]],
                  {"fields": ["id", "name", "active"],
                   "context": {"active_test": False}})
if not methods:
    print("⚠ Method code='paypal' not found — provider will crash UI")
    sys.exit(1)

method = methods[0]
print(f"  Method [{method['id']}] {method['name']} active={method['active']}")

if method["id"] not in provider["payment_method_ids"]:
    merged = list(set(provider["payment_method_ids"] + [method["id"]]))
    write("payment.provider", [provider["id"]],
          {"payment_method_ids": [(6, 0, merged)]})
    print(f"  ✓ Linked method 'paypal' to provider {provider['id']}")
else:
    print(f"  ✓ Method already linked")

print()
print("→ UI : Settings → Payment Providers → PayPal")
print("→ Coller PayPal email + API credentials → State = Enabled")
