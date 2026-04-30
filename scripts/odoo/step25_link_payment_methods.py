"""Link payment.method records to the providers and activate them.

Fixes the Owl crash on the provider form: payment.provider needs at least one
linked payment.method, otherwise the form view crashes with
'Cannot read properties of undefined (reading 1)' on a SelectionField.

  - Stripe (id=18) → method 'card' + activate
  - Virement (id=19) → method 'wire_transfer' + activate

Idempotent: skips if already linked.

Run: python step25_link_payment_methods.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, write, execute

# (provider_code, method_codes_in_priority_order)
LINKS = [
    ("stripe", ["card"]),
    ("custom", ["wire_transfer"]),
]

for provider_code, method_codes in LINKS:
    providers = search_read("payment.provider",
                            [("code", "=", provider_code)],
                            ["id", "name", "payment_method_ids"])
    if not providers:
        print(f"⚠ No provider with code='{provider_code}' — skipping")
        continue
    p = providers[0]
    print(f"\nProvider [{p['id']}] {p['name']}:")
    print(f"  Currently linked methods: {p['payment_method_ids']}")

    # Find the methods
    method_ids = []
    for code in method_codes:
        methods = execute("payment.method", "search_read",
                          [[("code", "=", code)]],
                          {"fields": ["id", "name", "active"],
                           "context": {"active_test": False}})
        if not methods:
            print(f"  ⚠ Method code='{code}' not found")
            continue
        m = methods[0]
        print(f"  Method [{m['id']}] {m['name']} active={m['active']}")
        method_ids.append(m["id"])
        # Note: method auto-activates when linked provider goes to state=enabled.
        # Trying to activate now fails because no provider is enabled yet.

    if method_ids:
        # Link via M2M (replace with new set; keep existing if any)
        existing_ids = p["payment_method_ids"]
        merged = list(set(existing_ids + method_ids))
        if set(merged) != set(existing_ids):
            write("payment.provider", [p["id"]],
                  {"payment_method_ids": [(6, 0, merged)]})
            print(f"  ✓ Linked methods: {merged}")
        else:
            print(f"  ✓ Already linked correctly")

print("\n=== Done. Try the UI again. ===")
